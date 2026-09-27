import tempfile
import unittest
from pathlib import Path

import tsr_test_fixtures as fx
from tsr_forensics.cue import compute_layout, frames_to_msf, msf_to_frames, parse_cue_text
from tsr_forensics.disc import DataTrackStream, layout_for_single_track, scan_track, summarize_sector_range
from tsr_forensics.iso9660 import parse_iso, pycdlib_crosscheck, read_extent


class CueParserTests(unittest.TestCase):
    def test_msf(self):
        self.assertEqual(msf_to_frames("00:02:00"), 150)
        self.assertEqual(msf_to_frames("01:00:74"), 60 * 75 + 74)
        self.assertEqual(frames_to_msf(150), "00:02:00")

    def test_multiple_files_tracks_indexes(self):
        sheet = parse_cue_text(
            'REM comentario\nCATALOG 0000000000000\n'
            'FILE "Jogo (Track 1).bin" BINARY\n  TRACK 01 MODE2/2352\n    INDEX 01 00:00:00\n'
            'FILE "Jogo (Track 2).bin" BINARY\n  TRACK 02 AUDIO\n    FLAGS DCP\n    INDEX 00 00:00:00\n    INDEX 01 00:02:00\n'
            'FILE Jogo3.bin BINARY\n  TRACK 03 MODE1/2048\n    INDEX 01 00:00:00\n'
        )
        self.assertEqual(len(sheet.files), 3)
        self.assertEqual([t.type for t in sheet.tracks], ["MODE2/2352", "AUDIO", "MODE1/2048"])
        self.assertEqual(sheet.files[2].name, "Jogo3.bin")
        self.assertEqual(sheet.tracks[1].indexes, {0: 0, 1: 150})
        self.assertEqual(sheet.tracks[1].flags, ["DCP"])
        self.assertEqual(sheet.catalog, "0000000000000")
        self.assertEqual(sheet.warnings, [])

    def test_all_track_types_and_malformed_variant(self):
        text = "".join(
            f'FILE "t{n}.bin" BINARY\n TRACK {n} {kind}\n INDEX 1 00:00:00\n'
            for n, kind in enumerate(["MODE1/2048", "MODE1/2352", "MODE2/2336", "MODE2/2352", "AUDIO", "CDG"], start=1)
        )
        sheet = parse_cue_text(text)
        sizes = [t.sector_size for t in sheet.tracks]
        self.assertEqual(sizes, [2048, 2352, 2336, 2352, 2352, None])
        self.assertTrue(any("1 dígito" in w for w in sheet.warnings))
        self.assertTrue(any("CDG" in w for w in sheet.warnings))

    def test_single_file_layout_with_index00_and_pregap(self):
        sheet = parse_cue_text(
            'FILE "disco.bin" BINARY\n'
            "  TRACK 01 MODE2/2352\n    INDEX 01 00:00:00\n"
            "  TRACK 02 AUDIO\n    INDEX 00 00:01:00\n    INDEX 01 00:03:00\n"
            "  TRACK 03 AUDIO\n    PREGAP 00:02:00\n    INDEX 01 00:05:00\n"
        )
        total_sectors = 75 * 5 + 100
        layouts = compute_layout(sheet, [Path("disco.bin")], [total_sectors * 2352])
        t1, t2, t3 = layouts
        self.assertEqual((t1.begin_byte, t1.sectors), (0, 75))
        self.assertEqual(t2.begin_byte, 75 * 2352)
        self.assertEqual(t2.index01_byte, 225 * 2352)
        self.assertEqual(t2.pregap_in_file, 150)
        self.assertEqual(t2.sectors, 300)
        self.assertEqual(t2.abs_lba_index01, 225)
        # PREGAP não está no arquivo e desloca os endereços seguintes (psx-spx)
        self.assertEqual(t3.begin_byte, 375 * 2352)
        self.assertEqual(t3.sectors, 100)
        self.assertEqual(t3.abs_lba_index01, 375 + 150)
        self.assertEqual(t3.pregap_not_in_file, 150)


class DiscReadTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.disc = fx.build_disc(self.tmp / "disc")

    def tearDown(self):
        self._tmp.cleanup()

    def _data_layout(self):
        path = self.disc["track1"]
        return layout_for_single_track(path, path.name, path.stat().st_size, "MODE2/2352")

    def test_scan_counts_form2_xa_and_msf(self):
        layout = self._data_layout()
        scan = scan_track(layout.file_path, layout, keep_map=True)
        stats = scan["estatisticas"]
        self.assertEqual(stats["setores_lidos"], self.disc["data_sectors"])
        self.assertEqual(stats["setores_com_sync"], self.disc["data_sectors"])
        self.assertEqual(stats["modo_2"], self.disc["data_sectors"])
        self.assertEqual(stats["form2"], 4)
        self.assertEqual(stats["xa_audio_form2"], 4)
        self.assertNotIn("msf_cabecalho_divergente", stats)
        self.assertEqual(stats["str_mdec_0160_8001"], 4)
        xa_lba, xa_count = self.disc["xa"]
        summary = summarize_sector_range(scan["mapa_setores"], xa_lba, xa_count)
        self.assertEqual(summary["xa_audio_form2"], xa_count)
        self.assertEqual(scan["hashes"]["size"], len(self.disc["raw"]))

    def test_logical_stream_matches_iso_and_pycdlib(self):
        layout = self._data_layout()
        stream = DataTrackStream(layout.file_path, 0, 2352, 24, 0, layout.sectors)
        try:
            self.assertEqual(stream.read(), self.disc["iso"])
            stream.seek(16 * 2048 + 1)
            self.assertEqual(stream.read(5), b"CD001")
            parsed = parse_iso(stream)
            self.assertEqual(parsed["pvd"]["identificador_sistema"], "PLAYSTATION")
            self.assertEqual(parsed["pvd"]["assinatura_cd_xa"], "CD-XA001")
            files = {e["path"]: e for e in parsed["entries"] if not e["is_dir"]}
            for path, (lba, size) in self.disc["locations"].items():
                self.assertEqual((files[path]["lba"], files[path]["size"]), (lba, size), path)
            self.assertIsNotNone(files["/TEST_000.00;1"]["xa"])
            data = b"".join(read_extent(stream, *self.disc["locations"]["/SYSTEM.CNF;1"]))
            self.assertEqual(data, fx.SYSTEM_CNF)
            second = DataTrackStream(layout.file_path, 0, 2352, 24, 0, layout.sectors)
            try:
                cross = pycdlib_crosscheck(second, parsed["entries"])
            finally:
                second.close()
            self.assertEqual(cross["status"], "ok", cross)
            self.assertEqual(cross["arquivos_comparados"], len(self.disc["locations"]))
        finally:
            stream.close()

    def test_mode1_2352_and_2336_views(self):
        iso = self.disc["iso"]
        mode1 = self.tmp / "m1.bin"
        mode1.write_bytes(fx.iso_to_mode1_raw(iso))
        stream = DataTrackStream(mode1, 0, 2352, 16, 0, len(iso) // 2048)
        try:
            self.assertEqual(stream.read(), iso)
        finally:
            stream.close()
        raw = self.disc["raw"]
        mode2336 = self.tmp / "m2336.bin"
        mode2336.write_bytes(b"".join(raw[i * 2352 + 16:(i + 1) * 2352] for i in range(len(raw) // 2352)))
        stream = DataTrackStream(mode2336, 0, 2336, 8, 0, len(iso) // 2048)
        try:
            self.assertEqual(stream.read(16 * 2048)[:], iso[: 16 * 2048])
        finally:
            stream.close()


if __name__ == "__main__":
    unittest.main()
