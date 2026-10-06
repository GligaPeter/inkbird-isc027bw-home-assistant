"""Small protocol regression tests that do not require Home Assistant."""

from __future__ import annotations

import ast
import struct
import unittest
from pathlib import Path


SOURCE = (
    Path(__file__).parents[1]
    / "custom_components"
    / "inkbird_ble"
    / "__init__.py"
)
FUNCTIONS = {
    "crc16_modbus",
    "_f10_to_c",
    "_c_to_f10",
    "decode_fff2",
    "decode_fff3_alarms",
    "build_fff1",
    "build_fff3",
}
CONSTANTS = {"_F10_MAX_VALID", "_F10_DISABLED"}


def load_protocol_namespace() -> dict:
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
    selected = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name in FUNCTIONS:
                selected.append(node)
        elif isinstance(node, ast.Assign):
            names = {target.id for target in node.targets if isinstance(target, ast.Name)}
            if names & CONSTANTS:
                selected.append(node)
    module = ast.Module(body=selected, type_ignores=[])
    ast.fix_missing_locations(module)
    namespace = {"struct": struct}
    exec(compile(module, str(SOURCE), "exec"), namespace)
    return namespace


PROTOCOL = load_protocol_namespace()


class ProtocolTests(unittest.TestCase):
    def test_temperature_conversion_round_trip(self) -> None:
        for celsius in (20.0, 73.0, 92.0, 110.0, 300.0):
            encoded = PROTOCOL["_c_to_f10"](celsius)
            decoded = PROTOCOL["_f10_to_c"](encoded)
            self.assertAlmostEqual(decoded, celsius, delta=0.1)

    def test_fff2_decodes_probes_and_fan(self) -> None:
        payload = bytearray(20)
        for index, temperature in enumerate((110.0, 73.0, 80.0, 92.0)):
            struct.pack_into("<H", payload, index * 2, PROTOCOL["_c_to_f10"](temperature))
        payload[8] = 42
        decoded = PROTOCOL["decode_fff2"](bytes(payload))
        self.assertEqual(decoded["fan_speed"], 42)
        self.assertAlmostEqual(decoded["probe0"], 110.0, delta=0.1)
        self.assertAlmostEqual(decoded["probe3"], 92.0, delta=0.1)

    def test_fff3_alarm_write_can_be_read_back(self) -> None:
        payload = PROTOCOL["build_fff3"](
            bytes(20),
            target_c=110.0,
            probe_alarms={
                "probe1_alarm": 73.0,
                "probe2_alarm": 92.0,
                "probe3_alarm": 80.0,
            },
        )
        alarms = PROTOCOL["decode_fff3_alarms"](payload)
        self.assertAlmostEqual(alarms["probe1_alarm"], 73.0, delta=0.1)
        self.assertAlmostEqual(alarms["probe2_alarm"], 92.0, delta=0.1)
        self.assertAlmostEqual(alarms["probe3_alarm"], 80.0, delta=0.1)
        expected_crc = PROTOCOL["crc16_modbus"](payload[:18])
        self.assertEqual(struct.unpack_from("<H", payload, 18)[0], expected_crc)


if __name__ == "__main__":
    unittest.main()
