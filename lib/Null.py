"""
Null is the base substance, common for nodes and kernels.
It provides basic signalling carcass for the system design, which includes
 - state management
 - signalling interface
 - exec and run interface
 - debug interface

I. State
    States are the dict <str, any> object which can include dicts, maps, integers, floats, strings, bytes, booleans or None

due to signal-isolation-principle, the exec() receives and process one signal per time
"""
import abc
import inspect
import pickle
from abc import abstractmethod


class Signal:
    """
    Base Signal structure.

    _fields is the data hold by the signal. It has the following structure:
        key     - field name
        value   - tuple (type, default_value, human_readable_description)
    """

    _fields = {
        'src': (str, None, 'source/sender Null substance'),
        'dst': (str, None, 'destination/receiver Null substance')
    }

    _description = 'base signalling class'

    class FieldsMismatchError(Exception):
        pass

    @classmethod
    def inspect_fields(cls):
        """
        Collects all fields from the class and all its parents.
        CAUTION: Inheritors might override the _fields (type, default value and description)
        :return:
        """
        d = dict()
        if cls != Signal:
            d.update(cls.__base__.inspect_fields())
        d.update(cls._fields)
        return d

    @classmethod
    def check_fields(cls, **kwargs):
        fields = cls.inspect_fields()
        for field in fields.keys():
            if field not in kwargs:
                return False
            if type(kwargs[field]) != fields[field][0]:
                return False
        return True

    def set_fields(self, **kwargs):
        fields = self.inspect_fields()
        for field in fields.keys():
            if field not in kwargs:
                self.contained[field] = fields[field][1]
            elif type(kwargs[field]) != fields[field][0] or not issubclass(type(kwargs[field]), fields[field][0]):
                return False
        return True

    def __init__(self, **kwargs):
        self.contained = dict()
        try:
            if not self.set_fields(**kwargs):
                raise Signal.FieldsMismatchError
        except Signal.FieldsMismatchError:
            print("Fields mismatch!")

    # -------------------------------------------- CLASS STRUCTURE ---------------------------------------------------

    @staticmethod
    def find_ch(cl=None):
        if cl is None:
            cl = Signal
        children = cl.__subclasses__()
        ret = set().union(*[Signal.find_ch(ch) for ch in children])
        return ret.union({cl.__name__})

    @staticmethod
    def all_signals():
        return Signal.__all_signals(Signal)

    @staticmethod
    def __all_signals(cl):
        children = cl.__subclasses__()
        ret = {cl.__name__:cl}
        for ch in children:
            ret.update(Signal.__all_signals(ch))
        return ret

    # -----------------------------------------------GETTERS / SETTERS------------------------------------------------

    def get_src(self):
        return self.contained['src']

    def set_src(self, val):
        self.contained['src'] = val

    def get_dst(self):
        return self.contained['dst']

    def set_dst(self, val):
        self.contained['dst'] = val

    src = property(get_src, set_src)
    dst = property(get_dst, set_dst)


class SigMirror(Signal):
    def __init__(self, src=None, dst=None, key=None, val=None):
        super(SigMirror, self).__init__(src, dst)
        self.key = key
        self.value = val


class GeneralControlSignal(Signal):
    pass


class SigTerminate(GeneralControlSignal):
    """
    Expected reaction:
    - initialize terminate_table
    - send SigTerminate() to all children, terminate_table[node_id] = 1
    - cycle (contains)
        + recv signals from all children. Collect all SigTerminated. Use it's src to fill terminate_table[node_id]=2
        + if all terminate_table[node_id] is 2,
        + if there is SigTerminate.src = SigTerminate.dst = Null['name']
            1. set self['termination']=2
    """

    def __init__(self):
        super(SigTerminate, self).__init__()


class SigTerminated(GeneralControlSignal):
    """

    """
    def __init__(self, src=None, dst=None, countdown_request=0):
        super(SigTerminated, self).__init__(src=src, dst=dst)
        self.countdown_request = countdown_request

    def __int__(self):
        return self.countdown_request


class SigTerminateNow(GeneralControlSignal):
    def __init__(self, src=None, dst=None):
        super(SigTerminateNow, self).__init__(src=src, dst=dst)


class Null:

    def __init__(self, **kwargs):
        self._input_signals = list() # type: List[Signal]

        self._state = dict()

        self._domain = None  # type: Null
        if 'domain' in kwargs:
            self._domain = kwargs['domain']
            if isinstance(self._domain, Null):
                self._state['domain'] = self._domain['id']
            else:
                self._state['domain'] = str(self._domain)

        self._state['is_mirroring'] = False
        if 'is_mirroring' in kwargs:
            if kwargs['is_mirroring']:
                self._state['is_mirroring'] = kwargs['is_mirroring']

        self._state['id'] = ''
        if 'id' in kwargs:
            self._state['id'] = kwargs['id']

        self._state['base_priority'] = kwargs['base_priority'] if 'base_priority' in kwargs else 0
        self._state['additional_priority'] = kwargs['additional_priority'] if 'additional_priority' in kwargs else -1
        self._state['intercycle_waiting'] = kwargs['intercycle_waiting'] if 'intercycle_waiting' in kwargs else None

        self._state['termination'] = False

    # -------------------------------------------- CLASS STRUCTURE ---------------------------------------------------

    @staticmethod
    def find_ch(cl=None):
        if cl is None:
            cl = Signal
        children = cl.__subclasses__()
        ret = set().union(*[Null.find_ch(ch) for ch in children])
        return ret.union({cl.__name__})

    @staticmethod
    def list_all_nulls():
        return Null.__all_nulls(Signal)

    @staticmethod
    def __all_nulls(cl):
        children = cl.__subclasses__()
        ret = {cl.__name__:cl}
        for ch in children:
            ret.update(Null.__all_nulls(ch))
        return ret

    # ---------------------------------------------- STATE MGMT ------------------------------------------------------

    def get(self, key, default_value = None):
        if key in self._state:
            return self._state[key]
        else:
            return default_value

    def __getitem__(self, item=None):
        return self._state[item] if item in self._state else None

    def set(self, key=None, value=None):
        self._state[key] = value
        if self['is_mirroring']:
            cur = inspect.currentframe()
            inv = inspect.getouterframes(cur, 2)
            inv_self = inv[1].frame.f_locals['self']
            cur_self = cur.f_locals['self']
            if inv_self == cur_self:
                self._domain.emit(SigMirror(self['id'], self['id'], key, value))

    # --------------------------------------------- SIGNAL MGMT ------------------------------------------------------

    def push_signal(self, signal):
        if isinstance(signal, SigTerminateNow):
            # SigTerminateNow pushes the signal in the front of the stack
            self._input_signals.insert(0, signal)
        else:
            self._input_signals.append(signal)

    def emit(self, signal):
        if isinstance(self._domain, Null):
            self._domain.emit(signal)
        else:
            self.push_signal(signal)

    # ----------------------------------------------- RUNNING --------------------------------------------------------

    def exec(self, signal):
        """
        Global hook to implement specific common behavior.
        For now it's just calling the abstract class-specific function _exec(signal)
        """
        self._exec(signal)

    @abstractmethod
    def _exec(self, signal):
        """
        Exec is the main functional part of the Null which is responsible for determining subject's behavior,

        Invoked via the exec() from the outside of the class to

        WARNING:
            Recurrent calls are not expected by the architecture. Use signal emission self['id']->self['id'] instead
        """
        pass

    # @abstractmethod
    # def cycle(self):
    #     pass

    #@abstractmethod
    #def run(self):
    #    pass


class Node(Null):
    @abstractmethod
    def exec(self, signal):
        pass



"""
a. Base priority is the number of exec(signal) done inside the cycle().
    - If there is no signals left to process will do exec(NoSignal())
    - If base_priority is -1, the cycle() will run until the 'termination' state is set

b. Additional priority is the maximum number of exec() can be done after all the first <base_priority> signals
    - If there are no signals left will stop the cycle()
    - If additional_priority is -1, the cycle() will run until there is any signal left (or until the 'termination' state)
    - If there is signals is added during the cycle(), in won't be processed in current cycle()  ??

TODO:
c. Signal processing behavior / buffering:

    - Signals pushed during this cycle won't affect current cycle (will appear only in the next cycle)
        I.  The buffer is read whole at the start of the cycle()
                                or
        II. The buffer is read one by one right before exec(signal) inside the cycle                

    - base section of the cycle can send NoSignal() or wait until any signal appears.
c. Signal processing behavior / sync-async
    // In fact it is the question of buffering approach: buffer all the time or only at the sync/receive phase
        Sync mode:
        1. pop all input buffer
        2. base phase
        3. additional phase
        4. push all output buffer

        async mode:
        1. base phase
        2. additional phase
        // pushes immediately [right into the queue if any]
        // and reads a single signal right before each exec() [right from the input queue]    
c.  Signal processing behavior / no-signal:
    I.  If there is no signal in the input stack, emit NoSignal()
    II. If there is no signal, wait until  
c. Signal proc. behavior / analysis:
    1. sync & buffer
        #--- n calculations ---                                
        if base == -1:
            n = q                                                                                
        else:
            if base < n:
                n = min(base, q)
                n_no = base - n
            else
                if addt == -1:
                    n = q
                    n_no = 0 
                else:
                    n = base + min(addt, q - base)
                    n_no = 0                

        #--- cycle ---
        buffer = queue.take_first(n)
        for sig in buffer:
            execute(sig)
        for k in range(n_no):
            execute(NoSignal())

    2. sync & no buffer
        # Allows quick termination
        exec_passed = 0        

        # base phase                        
        base_iter = 0
        while base_iter != base:                    
            if queue.empty():
                if not pre_exec_no():
                    return
            else:
                if not pre_exec(queue.recv()):
                    return
            base_iter += 1   # set base to -1 to run infinitely

        # addt phase
        addt_iter = 0
        while addt_iter != addt:
            if queue.empty():
                return
            else:
                if not pre_exec(queue.recv()):
                    return
            addt_iter += 1   # set base to -1 to run infinitely


            ??
            is_no = False
            if input.empty():
                if base_left != 0 or base == -1:
                    is_no = True
                if base != 0:
                    base_left -= 1
            if is_no:
                execute(NoSignal())
                continue

            if input.empty() and (base_left != 0 or base == -1):
                execute(NoSignal)
                base_left -= base != -1
            elif exec_passed <= base:
                execute(input.last())

            exec_passed += 1

d. Intercycle waiting is the amount of second (float, 1.0 = 1 sec) waited after all the base and additional signals passed
    - If the value is None will skip timer creation. If the value iz 0 will create the timer and wait 0 seconds.

"""


class A:
    awoo={'a': 'b'}

    @classmethod
    def t(cls):
        d = dict()
        d.update(cls.awoo)
        if cls != A:
            d.update(cls.__base__.t())
        return d


class B(A):
    awoo={'c':'d'}


print(A().t())