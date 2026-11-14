"""Regras de dependência entre camadas. Quebra se alguém atravessar uma fronteira."""
import ast, unittest
from pathlib import Path

APP = Path(__file__).resolve().parents[1] / 'app'

# camada -> o que ela NÃO pode importar (pacotes do app e bibliotecas)
FORBIDDEN = {
    'domain':      {'infra', 'services', 'controllers', 'routes', 'fastapi', 'duckdb', 'pandas', 'sqlite3', 'urllib'},
    'infra':       {'services', 'controllers', 'routes', 'fastapi'},
    'services':    {'controllers', 'routes', 'fastapi'},
    'controllers': {'infra', 'routes'},
    'routes':      {'services', 'infra', 'domain'},
}


def imports(path: Path) -> set[str]:
    """Nomes importados: 'fastapi', 'duckdb', e camadas do app via import relativo ('infra', 'domain'...)."""
    out = set()
    for n in ast.walk(ast.parse(path.read_text())):
        if isinstance(n, ast.Import):
            out |= {a.name.split('.')[0] for a in n.names}
        elif isinstance(n, ast.ImportFrom):
            mod = (n.module or '').split('.')
            if n.level == 0:
                out.add(mod[0])
            elif n.level == 2:                          # from ..infra.x import y
                out.add(mod[0])
    return out


class TestArquitetura(unittest.TestCase):
    def test_camadas_respeitam_as_fronteiras(self):
        for layer, banned in FORBIDDEN.items():
            for f in sorted((APP / layer).glob('*.py')):
                with self.subTest(arquivo=f'{layer}/{f.name}'):
                    self.assertEqual(imports(f) & banned, set())

    def test_um_conceito_por_arquivo(self):
        """Arquivos pequenos: se passar disso, é hora de atomizar de novo."""
        for f in sorted(APP.rglob('*.py')):
            with self.subTest(arquivo=str(f.relative_to(APP))):
                self.assertLess(len(f.read_text().splitlines()), 150)


if __name__ == '__main__':
    unittest.main()
