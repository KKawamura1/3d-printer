"""Left version is its own CAD target and is not a mirrored text string."""
import unittest
from parts.gentle_curve_tunnel.design import LEFT_PART_ID, build_part, _mouth_round
from parts.gentle_curve_tunnel_left.design import PART_ID, SOURCE_VERSION
from parts.tunnel.design import Tunnel


class GentleTunnelLeftTests(unittest.TestCase):
    def test_left_target_identity_and_circular_ports(self):
        self.assertEqual(PART_ID, LEFT_PART_ID)
        self.assertEqual(SOURCE_VERSION, "E01-V3")
        part, profile = build_part("left")
        self.assertTrue(part.isValid())
        self.assertEqual(len(part.Solids()), 1)
        self.assertEqual((profile.nx, profile.ny), (4, 4))
        self.assertTrue(_mouth_round(part, "left", Tunnel()))
