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


class FanRoundTripTests(unittest.IsolatedAsyncioTestCase):
    async def run_controller(self, confirm=True, fail_first_write=False):
        ns = load_protocol_namespace()
        cls = next(n for n in ast.parse(SOURCE.read_text()).body
                   if isinstance(n, ast.ClassDef) and n.name == 'InkbirdCoordinator')
        module = ast.Module(body=[ast.ImportFrom(module='__future__', names=[ast.alias(name='annotations')], level=0), cls], type_ignores=[])
        ast.fix_missing_locations(module)
        events = []
        baseline = bytes(range(20))
        reads = {'FFF1': 0, 'FFF3': 0}
        class FakeBleakError(Exception): pass
        class Client:
            services = []
            is_connected = True
            cycles = 0
            attempts = 0
            applied = False
            async def __aenter__(self): return self
            async def __aexit__(self, *args): return False
            async def read_gatt_char(self, uuid):
                events.append(('read', uuid))
                if uuid in reads:
                    reads[uuid] += 1
                if uuid == 'FFF1' and reads[uuid] > 1 and confirm and self.applied:
                    return bytes([1]) + baseline[1:]
                return baseline
            async def write_gatt_char(self, uuid, payload, response):
                events.append(('write', uuid, payload))
                if uuid == 'FFF1':
                    self.attempts += 1
                    if fail_first_write and self.attempts == 1:
                        raise FakeBleakError('temporary failure')
                    self.applied = True
        client = Client()
        async def sleep(delay):
            if delay == 3:
                client.cycles += 1
                if client.cycles == 4:
                    client.is_connected = False
        ns.update(asyncio=SimpleNamespace(wait_for=asyncio.wait_for, sleep=sleep),
                  _LOGGER=logging.getLogger('test'), FFF1='FFF1', FFF2='FFF2', FFF3='FFF3',
                  BleakClient=object, BleakError=FakeBleakError,
                  async_ble_device_from_address=lambda *a, **k: object(),
                  establish_connection=AsyncMock(return_value=client))
        exec(compile(module, str(SOURCE), 'exec'), ns)
        coordinator = ns['InkbirdCoordinator'].__new__(ns['InkbirdCoordinator'])
        coordinator.hass = object()
        coordinator.address = 'test'
        coordinator.data = SimpleNamespace(connected=False)
        coordinator._pending_fan_on = True
        coordinator._fan_on_attempts = 0
        coordinator._pending_target = 120
        coordinator._pending_probe_alarm = {'probe1_alarm': 73}
        coordinator._probe_alarm_attempts = {}
        coordinator._target_temp = 120
        coordinator._notify = lambda: None
        coordinator._update_predictions = lambda: None
        await coordinator._connect_and_run()
        return coordinator, events, baseline

    async def test_confirmed_fan_writes_once_and_preserves_other_settings(self):
        coordinator, events, baseline = await self.run_controller()
        self.assertEqual(events[:2], [('read', 'FFF3'), ('read', 'FFF1')])
        fan_writes = [e[2] for e in events if e[:2] == ('write', 'FFF1')]
        self.assertEqual(len(fan_writes), 1)
        self.assertEqual(fan_writes[0][1:18], baseline[1:18])
        target_write = next(e[2] for e in events if e[:2] == ('write', 'FFF3'))
        for index in (2, 3, *range(6, 18)):
            self.assertEqual(target_write[index], baseline[index])
        self.assertIsNone(coordinator._pending_fan_on)

    async def test_unconfirmed_fan_stops_after_three_writes(self):
        coordinator, events, _ = await self.run_controller(confirm=False)
        self.assertEqual(sum(e[:2] == ('write', 'FFF1') for e in events), 3)
        self.assertIsNone(coordinator._pending_fan_on)

    async def test_failed_fan_write_is_retried(self):
        coordinator, events, _ = await self.run_controller(fail_first_write=True)
        self.assertEqual(sum(e[:2] == ('write', 'FFF1') for e in events), 2)
        self.assertIsNone(coordinator._pending_fan_on)


if __name__ == '__main__':
    unittest.main()
