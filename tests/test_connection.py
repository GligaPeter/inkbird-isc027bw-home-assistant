"""Exercise the real coordinator loop with a simulated BLE controller."""
from __future__ import annotations

import ast
import asyncio
import logging
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock

from test_protocol import SOURCE, load_protocol_namespace


class ConnectionTests(unittest.IsolatedAsyncioTestCase):
    async def test_failed_initial_reads_never_write_and_retain_requests(self):
        for characteristic in ('FFF1', 'FFF3'):
            for failure in (RuntimeError('read failed'), b'\x00'):
                with self.subTest(characteristic=characteristic, failure=failure):
                    ns = load_protocol_namespace()
                    tree = ast.parse(SOURCE.read_text())
                    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'InkbirdCoordinator')
                    # Only annotations need HA types; postpone their evaluation.
                    module = ast.Module(body=[ast.ImportFrom(module='__future__', names=[ast.alias(name='annotations')], level=0), cls], type_ignores=[])
                    ast.fix_missing_locations(module)
                    client = SimpleNamespace(services=[], is_connected=True)
                    async def read(uuid):
                        if uuid == characteristic:
                            if isinstance(failure, Exception):
                                raise failure
                            return failure
                        return bytes(range(20))
                    client.read_gatt_char = read
                    client.write_gatt_char = AsyncMock()
                    class Context:
                        def __getattr__(self, name): return getattr(client, name)
                        async def __aenter__(self): return client
                        async def __aexit__(self, *args): return False
                    ns.update(asyncio=asyncio, _LOGGER=logging.getLogger('test'),
                              FFF1='FFF1', FFF3='FFF3', BleakClient=object,
                              async_ble_device_from_address=lambda *a, **k: object(),
                              establish_connection=AsyncMock(return_value=Context()))
                    exec(compile(module, str(SOURCE), 'exec'), ns)
                    coordinator = ns['InkbirdCoordinator'].__new__(ns['InkbirdCoordinator'])
                    coordinator.hass = object()
                    coordinator.address = 'test'
                    coordinator.data = SimpleNamespace(connected=False)
                    coordinator._fff1_current = bytes(range(20))
                    coordinator._fff3_current = bytes(range(20))
                    coordinator._pending_fan_on = True
                    coordinator._pending_target = 120
                    coordinator._pending_probe_alarm = {'probe1_alarm': 73}
                    with self.assertRaises((RuntimeError, ValueError)):
                        await coordinator._connect_and_run()
                    client.write_gatt_char.assert_not_called()
                    self.assertTrue(coordinator._pending_fan_on)
                    self.assertEqual(coordinator._pending_target, 120)
                    self.assertEqual(coordinator._pending_probe_alarm, {'probe1_alarm': 73})
                    self.assertFalse(coordinator.data.connected)


if __name__ == '__main__':
    unittest.main()
