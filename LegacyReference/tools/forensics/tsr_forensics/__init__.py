"""Kit forense do projeto Toy Story Race (tsr_forensics).

Ferramentas de linha de comando para:

* ``intake``: registrar, copiar, inventariar e extrair (somente em área de
  trabalho local) o arquivo original fornecido pelo proprietário;
* ``verify``: recalcular hashes do original e comparar com o registro;
* ``guard``: impedir que material original seja versionado no repositório
  público;
* ``install-hook``: instalar o ``guard`` como pre-commit hook local.

O kit NÃO contorna proteções (ex.: LibCrypt), NÃO altera o original e NÃO
envia nada para a internet. Os relatórios gerados contêm somente metadados.
"""

__version__ = "1.0.0"
KIT_NAME = "tsr-forensics"

__all__ = ["__version__", "KIT_NAME"]
