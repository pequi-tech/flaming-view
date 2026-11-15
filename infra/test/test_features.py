"""RD-04: nenhuma feature da emissão t lê a série depois de t."""
import os, sys, unittest
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import features as F


class TestSemVazamento(unittest.TestCase):
    def test_features_ignoram_o_futuro(self):
        rng = np.random.default_rng(0)
        A = rng.gamma(1, 10, (5, 24 * 12)).astype(np.float32)
        clim = F.climatology(A)
        lat, oni = np.zeros(5, np.float32), {t: 0.1 * t for t in range(A.shape[1])}
        for h in (1, 2, 3):
            t = 250
            before = F.features_at(A, t, h, lat, clim, oni)
            B = A.copy()
            B[:, t + 1:] = 1e6                        # futuro absurdo
            after = F.features_at(B, t, h, lat, clim, oni)
            self.assertTrue(before.equals(after), f'h={h} leu depois de t')

    def test_classe_segue_regra_do_back_end(self):
        clim = {'p25': np.array([[1.0]]), 'p75': np.array([[5.0]]), 'p90': np.array([[9.0]]), 'median': np.array([[3.0]])}
        k = F.classify(np.array([0.5]), clim, 0), F.classify(np.array([6.0]), clim, 0), F.classify(np.array([9.0]), clim, 0)
        self.assertEqual([int(x[0]) for x in k], [0, 2, 3])
        zero = {**clim, 'p90': np.array([[0.0]])}
        self.assertEqual(int(F.classify(np.array([5.0]), zero, 0)[0]), 1)


if __name__ == '__main__':
    unittest.main()
