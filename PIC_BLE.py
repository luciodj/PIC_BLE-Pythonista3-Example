#
# PIC-BLE Visualizer
#
import cb
import ui
import sys
from time import sleep

# RN4020 MLDP
#MLDP_SERVICE   = '00035B03-58E6-07DD-021A-08123A000300' 
#MLDP_DATA      = '00035B03-58E6-07DD-021A-08123A000301'
#MLDP_CONTROL   = '00035B03-58E6-07DD-021A-08123A0003FF'

# RN4870 Transparent UART 
RN4870_SERVICE  = '49535343-FE7D-4AE5-8FA9-9FAFD205E455'
RN4870_UART_TX  = '49535343-1E4D-4BD9-BA61-23C647249616'

class BLE_Manager (object):
    def __init__(self):
        self.peripheral = None
        self.buffer = ''
        self.sync = False

    def did_discover_peripheral(self, p):
        if p.name and 'PIC-BLE' in p.name and not self.peripheral:
            self.peripheral = p
            print('Connecting ...')
            cb.connect_peripheral(p)

    def did_connect_peripheral(self, p):
        print('Connected:', p.name)
        #print('Discovering services...')
        p.discover_services()

    def did_fail_to_connect_peripheral(self, p, error):
        print('Failed to connect: %s' % (error,))

    def did_disconnect_peripheral(self, p, error):
        print('Disconnected, error: %s' % (error,))
        self.peripheral = None
        v.close()

    def did_discover_services(self, p, error):
        for s in p.services:
            if s.uuid == RN4870_SERVICE:
                p.discover_characteristics(s)

    def did_discover_characteristics(self, s, error):
        #print('Did discover characteristics...')
        for c in s.characteristics:
          if c.uuid == RN4870_UART_TX:
              #print('found characteristic', c.uuid)
              self.data_char = c
              # Enable notification
              self.peripheral.set_notify_value(c, True)
              
    def did_update_value(self, c, error):
        parse(c.value)
        #print('value updated:', c.value)
                  
    def did_write_value(self, c, error):
        pass 
        
    def send_cmd(self, cmd):
        if self.peripheral:
          self.peripheral.write_characteristic_value(self.data_char, cmd, True)  
   
def button_press(sender):
  if sender.name == 'quit':
    v.close()
    
class PIC_BLE(ui.View):    
  '''Must be added as Custom View Class in the UI editor'''
  def __init__(self):
    self.x = 0
    self.y = 0
    self.z = 0
    
  def will_close(self):
    #print('Will Close')
    cb.reset()

class CView(ui.View):
    def draw(self):
        w, h = self.width, self.height
        xo, yo = w/2, h/2
        gx, gy = w/3, h/3 
      
        path = ui.Path()
        path.move_to(xo, yo)
        ui.set_color('red')
        path.line_width = 4
        x, y =  xo+gx*(v.x+v.y/2), yo+gy*(-v.z-v.y/2)
        path.line_to(x, y)
        path.stroke()
        path = ui.Path.oval(x-5, y-5, 10, 10)
        path.fill()
        
        path = ui.Path()
        ui.set_color('black')
        path.line_width = 1
        path.move_to(xo, yo)
        path.line_to(xo+gx, yo) # x axis
        path.stroke()
        
        path = ui.Path()
        ui.set_color('blue')
        path.line_width = 1
        path.move_to(xo, yo)
        path.line_to(xo-gx*.5, yo+gy*.5) # y axis
        path.stroke()

        path = ui.Path()
        ui.set_color('green')
        path.line_width = 1
        path.move_to(xo, yo)
        path.line_to(xo, yo-gy) # z axis
        path.stroke()
                        
  
# PIC-BLE demo sensor protocol decoder ------
def nibble(c):
  'decode a nibble'
  return '0123456789ABCDEF'.index(chr(c).upper())
  
def b2byte(bar):
  'decode a hex pair into a byte'
  val = nibble(bar[0]) * 16
  return val + nibble(bar[1])
    
class BLE_packet(object):
  def __init__(self, bar):
    "extract a list () from a BLE stream (bytearray) i.e. b'1A0200]' "
    self.seq = nibble(bar[0])
    self.cmd = chr(bar[1])
    length = b2byte(bar[2:4])
    if len(bar) != length + 4 : 
      raise ValueError
    self.payload = []
    index = 4
    while length > 0:
      self.payload.append(b2byte(bar[index:index+2]))
      index += 2
      length -= 2

  def __repr__(self):
    'visualize the decoded packet as a string'
    return 'BLE_packet( seq = {}, cmd = {}, payload = {}'.format( self.seq, self.cmd, self.payload)
    
def parse(bar):
  'stream splitter i.e. "[][][]...[]"'
  while bar:  
      i = bar.index(ord('['))    # raise vaue error if not found
      e = bar.index(ord(']'), i) # raise Value error if not found
      p = BLE_packet(bar[i+1:e])     
      dispatch(p) # interpret commands/messages
      bar = bar[e+1:]
    
def convert(msb, lsb):
      x = (msb<<8) + lsb      
      if x > 0x800 : x = x - 0x1000  
      return x/1024
            
def dispatch(msg):
  'interpret PIC-BLE demo protocol'
  if msg.cmd == 'P':     # pushbutton
      #v['text'].text = str(msg.payload[0])
      if msg.payload[0] == 1 :  
          v['sw0'].text = 'Pressed' 
          v['sw0'].background_color = '#ff0000'
      else:                     
          v['sw0'].text = 'Not Pressed'
          v['sw0'].background_color = '#ffffff' 
          
  elif msg.cmd == 'X':   # accelerometer data
      x = convert(msg.payload[1], msg.payload[0])
      y = convert(msg.payload[3], msg.payload[2])
      z = convert(msg.payload[5], msg.payload[4])
      v['text'].text = " x = {:.2f}, y = {:.2f}, z = {:.2f}".format(x, y, z)
      v.x = x
      v.y = y
      v.z = z
      v['cview'].set_needs_display()
      
# main --------------------------------
if __name__ == '__main__':
    cb.reset()
    v=ui.load_view('Searching')
    v.present('sheet', hide_title_bar=True)
    mngr = BLE_Manager()
    cb.set_central_delegate(mngr)
    cb.scan_for_peripherals()
    while not mngr.peripheral: pass
    v.close()
    
    sleep(1)
    v = ui.load_view('PIC_BLE')
    v.present(hide_title_bar=True)
    v.wait_modal()
    v.close()
    

    
