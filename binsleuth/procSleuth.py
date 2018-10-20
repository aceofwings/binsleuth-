#!/usr/bin/env python
import os
import psutil
from datetime import datetime
from graphviz import Source, Digraph

class ProcSleuth:

  def __init__(self, exe=None):
    self._connection_memory = {}
    self._process_memory = {} 
    self._go = True
    self._exe = exe
    self._lock_proc = None
    self._proc_cons = []
    self._proc_children = []
    self._proc_mem_map = []
    self._proc_con_memory = {}
    self._file_io = []
    self._file_memory = {}
  
  def set_state(self):
  
    ''' Set the current state of process list '''
    
    process_list = []
    for temp_process in psutil.process_iter():
      try:
        process_list.append(temp_process)
        self._process_memory[process_id] = temp_process.name()
        self._connection_memory[temp_process.name()] = temp_process.connections()
      except Exception as err:
        pass
    return process_list
  
  def _set_proc_state(self):
  
    ''' Set the current state of process '''
    
    assert self._lock_proc, "No process locked"
    
    self._proc_cons.extend(self._lock_proc.connections())
    self._proc_children.append(self._lock_proc.children(recursive=True))
    try: self._proc_mem_map.extend(self._lock_proc.mem_maps())
    except: pass
    
  def monitor_processes(self, previous_process_list):
    
    ''' Print changes to process list to stdout '''
    
    current_process_list = self.set_state()
    matched = 0
    
    for proc_current in current_process_list:
      for proc_previous in previous_process_list:
        if proc_previous == proc_current:
          matched = 1
          break
      if not matched:
        name = str(proc_current.name()).lower()
        print(' +++ ' + name + ' : ' + str(proc_current.pid))        
        if proc_current.connections():
          print(proc_current.connections())
          
        if name == self._exe:
          print('\nHooked Process\n')
          self._proc_con_memory[datetime.fromtimestamp(proc_current.create_time())] = []
          self._proc_con_memory[datetime.fromtimestamp(proc_current.create_time())].extend([(c, True) for c in proc_current.connections()])
          self._lock_proc = proc_current
          self._go = False
        
      matched = 0
    matched = 0
    
    for proc_previous in previous_process_list:
      try:
        name = str(proc_previous.name()).lower()
      except Exception as err:
        try:
          name = str(self._process_memory[proc_previous.pid])
        except Exception as err:
          name = proc_previous
      for proc_current in current_process_list:
        if proc_previous == proc_current:
          matched = 1
          break
      if not matched:
        print(' --- ' + str(name) + ' : ' + str(proc_previous.pid))
      matched = 0

    return current_process_list
 
 
  def _monitor(self):
    
    ''' monitor the target process '''
    
    assert self._lock_proc, "No process locked"
    
    self._go = True
    
    while self._go:
      
      self._monitor_network_cons()
      self._monitor_file_io()
      self._monitor_children()
      
    return 

    
  def process_exits(self):
    
    ''' checks if the process is still running 
      return boolean
    '''
    
    if psutil.pid_exists(self._lock_proc.pid):
      try:
        if self._lock_proc.name() == psutil.Process(self._lock_proc.pid).name() and psutil.Process(self._lock_proc.pid).status() == 'running':
          return True
      except: pass
      
    for proc in psutil.process_iter():
      try:
        if self._lock_proc.name().lower() == proc.name().lower():
          self._lock_proc = psutil.Process(proc.pid)
          return True
      except: return False
    return False
  
  
  def _terminate(self):
    
    for child in self._proc_children:
      child.terminate()
    dead, alive = psutil.wait_procs(self._proc_children, timeout=3)
    for kiddie in alive:
      kiddie.kill()

   
  def _monitor_file_io(self):
    
    matched = 0
    
    if not self.process_exits():
      self._terminate()
      self._go = False
      return
      
    try: cur_files = psutil.Process(self._lock_proc.pid).open_files()
    except:
      self._go = False
      return
    
    for new_file in cur_files:
      for old_file in self._file_io:
        if new_file == old_file:
          matched = 1
          break
      
      if not matched:
        timestamp = datetime.now()
        try: self._file_memory[timestamp].extend([(new_file, True)])
        except:
          self._file_memory[timestamp] = []
          self._file_memory[timestamp].extend([(new_file, True)])
        # print(' +++ ' + str(new_file))
      
      matched = 0
    matched = 0
    
    for old_file in self._file_io:
      for new_file in cur_files:
        if old_file ==new_file:
          matched = 1
          break
          
      if not matched:
        timestamp = datetime.now()
        try: self._file_memory[timestamp].extend([(old_file, False)])
        except:
          self._file_memory[timestamp] = []
          self._file_memory[timestamp].extend([(old_file, False)])
        # print(' --- ' + str(old_file))
      matched = 0
      
    self._file_io = cur_files


  def _monitor_network_cons(self):
    
    matched = 0

    if not self.process_exits():
      self._terminate()
      self._go = False
      return
      
    try: cur_cons = psutil.Process(self._lock_proc.pid).connections()
    except:
      self._go = False
      return
    for new_con in cur_cons:
      for old_con in self._proc_cons:
        if new_con == old_con:
          matched = 1
          break
          
      if not matched:
        timestamp = datetime.now()
        try: self._proc_con_memory[timestamp].extend([(new_con, True)])
        except:
          self._proc_con_memory[timestamp] = []
          self._proc_con_memory[timestamp].extend([(new_con, True)])     
        # print(' +++ ' + str(new_con))
      matched = 0
    matched = 0
    
    for old_con in self._proc_cons:
      for new_con in cur_cons:
        if old_con == new_con:
          matched = 1
          break
          
      if not matched:
        timestamp = datetime.now()
        try: self._proc_con_memory[timestamp].extend([(old_con, False)])
        except:
          self._proc_con_memory[timestamp] = []
          self._proc_con_memory[timestamp].extend([(old_con, False)]) 
        # print(' --- ' + str(old_con))
      matched = 0
    
    self._proc_cons = cur_cons
 
 
  def _monitor_children(self):
    
    assert self._lock_proc, "No process locked"
 
    if not self.process_exits():
      self._terminate()
      self._go = False
      return
    child_state = psutil.Process(self._lock_proc.pid).children(recursive=True)
    
    try: last = self._proc_children[-1]
    except: last = []
    if not (last == child_state):
      self._proc_children.append(child_state)
 
  def run(self):
    
    ''' Loop to collect process state, check for not-allowed, and print changes to screen'''
    
    init = self.set_state()
    while self._go:
      init = self.monitor_processes(init)
    self._set_proc_state()
    self._monitor()
    return
    
  def format_time(self, time):
  
    ''' graphviz keeps tying to turn colons into ip:port relationship
      so this method prevents that
    '''
    return '{}-{}-{} {}.{}.{}.{}'.format(str(time.year), str(time.month), str(time.day), str(time.hour), str(time.minute), str(time.second), str(time.microsecond))

  
  def graph_con_mem(self, outfile='net_connections', view=False):
    
    '''
      create a pdf graph mapping network connections to times
      :outfile: the filename of saved graph
      :view: if True, pop open graph when done
      
      green edge: new connection
      red edge: connection end
      blue edge: time travel
    '''
    digraph = Digraph('Network_Connections', filename=outfile)
    digraph.attr(rankdir='TB')
    for k, v in self._proc_con_memory.items():
      digraph.attr('node', shape='doublecircle', color='black')
      digraph.node(self.format_time(k))
      
      for c in v:        
        con = c[0]
        is_new = c[1]
        
        if con.status == 'NONE':
          digraph.attr('node', shape='square', color='cyan')
          data = 'laddr {}\tport {} \nfamily {} \nstatus {}'.format(con.laddr[0], con.laddr[1], str(con.family), con.status)
          digraph.edge(self.format_time(k), data , weight='5', color='green' if is_new else 'red')
        
        else:
          digraph.attr('node', shape='circle', color='black')
          data = 'laddr {}\tport {} \nraddr {}\tport {} \nfamily {} \nstatus {}'.format(con.laddr[0], con.laddr[1], con.raddr[0], con.raddr[1], str(con.family), con.status)
          digraph.edge(self.format_time(k), data , weight='5', color='green' if is_new else 'red')

    digraph.attr('node', shape='doublecircle', color='black')
    sorted_memory = sorted(self._proc_con_memory.keys())
    for i in range(1, len(self._proc_con_memory.keys())):
      
      node1 = sorted_memory[i - 1]
      node2 = sorted_memory[i]

      digraph.edge(self.format_time(node1), self.format_time(node2), label=str(node2 - node1), color='blue')

    digraph.render(view=view)
    return
    
  def graph_file_memory(self, outfile='file_operations', view=False):
    
    '''
      create a pdf graph mapping file operations to times
      :outfile: the filename of saved graph
      :view: if True, pop open graph when done
      
      green edge: file accessed
      red edge: file close
      purple edge: time travel
    '''
    digraph = Digraph('File_Operation', filename=outfile)
    digraph.attr(rankdir='TB')
    for k, v in self._file_memory.items():
      digraph.attr('node', shape='doublecircle')
      digraph.node(self.format_time(k))
      
      for f in v:
        file_data = f[0]
        is_new = f[1]
        digraph.attr('node', shape='circle')
        try: data = '{}\nmode {}\nflags {}\nposition {}'.format(str(file_data.path).replace(':', '[colon]'), str(file_data.mode), str(file_data.flags), str(file_data.position))
        except: data = '{}'.format(str(file_data.path).replace(':', '[colon]').replace('\\', '/'))
        digraph.edge(self.format_time(k), data, color='green' if is_new else 'red')
    
    digraph.attr('node', shape='doublecircle')
    sorted_memory = sorted(self._file_memory.keys())
    for i in range(1, len(self._file_memory.keys())):
      
      node1 = sorted_memory[i - 1]
      node2 = sorted_memory[i]
      
      digraph.edge(self.format_time(node1), self.format_time(node2), label=str(node2 - node1), color='purple')
    digraph.render(view=view)
    return 
    
if os.name == 'nt': s = ProcSleuth('slack.exe')
else: s = ProcSleuth('firefox-esr')
s.run()
# for k,v in s._file_memory.items():
# print(k,v)
s.graph_con_mem(outfile="graph")
s.graph_file_memory(outfile="filegraph")
print(s._proc_children)
