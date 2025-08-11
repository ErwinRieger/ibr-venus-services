

import pydbus, time, logging, sched
from gi.repository import GLib

logger = logging.getLogger(__name__)

settingscmd=b"\xaa\x55\x11\x01\x04\x00\x14\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff\xff" # Retrieve settings (state of the writable registers)
oncmd=b"\xaa\x55\x11\x00\x05\x0D\x14\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\xF3\xFF"
offcmd=b"\xaa\x55\x11\x00\x05\x0D\x14\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xF2\xFF"

onoffcmds = [ offcmd, oncmd ]

# uuid of "command characteristic"
cmd_uid = "0000ffe1"

class NeeyBalancer:

  def __init__(self, devname, dev_id, doneCb):

    self.scheduler = sched.scheduler(time.time)

    self.doneCb = doneCb

    # DBus object paths
    self.bluez_service = 'org.bluez'
    adapter_path = '/org/bluez/hci0'

    # Get adapter and device objects
    self.bus = pydbus.SystemBus()

    self.adapter = self.bus.get(self.bluez_service, adapter_path) 

    self.mngr = self.bus.get(self.bluez_service, '/')

    self.dev_id = dev_id
    self.devname = devname
    self.device_path = f"{adapter_path}/dev_{dev_id.replace(':', '_')}"

  def init(self):
      self.timeout = None
      self.deststate = None
      self.connected = False
      self.error = None
      self.cmd_character = None

  def run(self):
      self.scheduler.run(False)

  def scanTask(self, cb, arg):

      ol = self.mngr.GetManagedObjects()
      # logger.info(f"Scan found {len(ol)} devices")
      if self.device_path in ol:
          if self.checkTimeout():
              self.scheduler.enter(0.1, 0, self.connectTask, (cb, arg))
          return

      if self.checkTimeout():
          self.scheduler.enter(1, 0, self.scanTask, (cb, arg))

  def connectTask(self, cb, arg):

      try:
          res = self.connect()
      except GLib.GError as ex:
          logger.info(f"Exception on connect... {ex}")
          self.adapter.StopDiscovery()
          if self.checkTimeout():
              self.scan((cb, arg))
          return

      if res:
          cb(arg)

  def settingsTask(self, cb, arg):

      if self.settingsReceived():
          # done
          s = self.balswitch
          # logger.info(f"Got self switch state: {s}, should be: {self.deststate}")
          logger.info(f"Got self switch state: {s}")

          cb(arg)

          """

          if s != self.deststate:
              if not userdata.switchsent:
                  self.switch(self.deststate)
                  self.sendSettingsCmd()
                  # userdata.switchsent = True
                  assert(0)
          else:
              logger.info("done, exiting")
              # userdata.exitcode = 0
              mainloop.quit()
              return False
          """
          return

      if self.checkTimeout():
          self.scheduler.enter(1, 0, self.settingsTask, (cb, arg))

  def switchRun(self, state):
    
    # logger.info(f"balancer: switching to state: {state}")

    self.init()

    assert(not self.scheduler.queue)

    self.deststate = state

    self.setTimeout(60)

    # self.adapter.StartDiscovery()
    # self.scheduler.enter(1, 0, self.scanTask, (self.reqState, True))
    self.scan((self.reqState, True))

  def reqState(self, setState):

      # logger.info(f"reqstate ... {setState}")
      self.sendSettingsCmd()
      self.scheduler.enter(1, 0, self.settingsTask, (self.checkState, setState))

  def checkState(self, setState):

      # logger.info(f"checkstate ...{setState}")
      if self.balswitch != self.deststate:
          if setState:
              self.switch(self.deststate)
              self.sendSettingsCmd()
              self.scheduler.enter(1, 0, self.settingsTask, (self.checkState, False))
          else:
              self.error = (1, "SET failed")
              self.callDoneCb()
      else:
          self.callDoneCb()

  def scan(self, cbargs):

    # logger.info("Starting scan...")
    try:
        self.adapter.StartDiscovery()
    except GLib.GError as ex:
        # :org.bluez.Error.InProgress as e:
        logger.info(f"scan already in progress... {ex}")
        
    if self.checkTimeout():
        self.scheduler.enter(1, 0, self.scanTask, cbargs)

  def setTimeout(self, t):
      if self.timeout == None:
          self.timeout = time.time() + t

  def checkTimeout(self):
      if self.timeout and time.time() > self.timeout:
          logger.info("timed out ...")
          self.error = (2, "Timeout")
          self.callDoneCb()
          return False
      return True

  def callDoneCb(self):

      for event in self.scheduler.queue:
          logger.info(f"cancel event: {event}")
          self.scheduler.cancel(event)

      self.close()
      self.doneCb(self.devname, self.error, self.deststate)

  def scanoff(self):

    # logger.info("stopping scan...")

    try:
        self.adapter.StopDiscovery()
    except GLib.GError as ex:
        logger.info(f"error stopping scan... {ex}")

  def connect(self):

    logger.info(f"connecting to {self.dev_id}")

    try:
        self.device = self.bus.get(self.bluez_service, self.device_path)
    except KeyError:
        logger.info(f"Error retieving device {self.device_path}")
        raise

    self.device.Connect()
    self.connected = True

    # Wait for the remote device to resolve its services
    while not self.device.ServicesResolved:
        if not self.checkTimeout():
            return False
        time.sleep(0.5)

    cmd_path = self.get_characteristic_path(cmd_uid)
    self.cmd_character = self.bus.get(self.bluez_service, cmd_path)

    self.cmd_character.onPropertiesChanged = self.temp_handler
    self.cmd_character.StartNotify()

    self.balswitch = None
    return True

  def close(self):
    # Disconnect

    if self.connected:
        logger.info("Disconnect")
        self.scanoff()

        if self.cmd_character:
            # logger.info("StopNotify")
            self.cmd_character.StopNotify()

        try:
          self.device.Disconnect()
        except GLib.GError as ex:
            logger.info(f"Exception on disconnect... {ex}")
    
        self.connected = False

  def get_characteristic_path(self, uuid):
    """Get DBus object path for Characteristic UUID"""
    mng_objs = self.mngr.GetManagedObjects()
    for path in mng_objs:
        # chr_uuid = mng_objs[path].get('org.bluez.GattCharacteristic1', {}).get('UUID')
        mng_obj = mng_objs[path]
        gattchar = mng_obj.get('org.bluez.GattCharacteristic1', {})
        # gattchar = mng_obj.get('org.bluez.GattDescriptor1', {})
        if gattchar:
            chr_uuid = gattchar.get('UUID')
            if path.startswith(self.device._path):
                if chr_uuid.startswith(uuid.casefold()):
                    return path
    assert(0)

  def temp_handler(self, iface, prop_changed, prop_removed):
    """Notify event handler for temperature"""
    if 'Value' in prop_changed:
        data = prop_changed['Value']

        # 2 Bytes: Start of frame (0x55 0xAA)
        start = data[0]
        if start != 0x55:
            return

        cmd = data[4]

        if cmd == 1: # system data
            logger.info(f"Got system data message, len: {len(data)}")
        elif cmd == 2: # battery data
            # logger.info(f"Got battery data message, len: {len(data)}")
            pass
        elif cmd == 3: # factory reset
            logger.info(f"Got factory reset message, len: {len(data)}")
        elif cmd == 4: # settings
            # logger.info(f"Got settings data message, len: {len(data)}, balswitch: {self.balswitch}")
            self.balswitch = data[21]

  def sendSettingsCmd(self):
    self.cmd_character.WriteValue(settingscmd, {})

  def switch(self, state):
    logger.info(f"balancer: switching to state: {state}, cmd: {onoffcmds[state]}")
    self.cmd_character.WriteValue(onoffcmds[state], {})

  def settingsReceived(self):
    return self.balswitch != None




