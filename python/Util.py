'''

Created on Nov. 23, 2017

@author Andrew Habib

'''

import json
import os, shutil

from collections import OrderedDict, namedtuple
from xml.etree import cElementTree as ET
from datetime import datetime
from icecream import ic as logger

if not os.path.exists(f'{os.getcwd()}/logs'):
    os.makedirs(f'{os.getcwd()}/logs')

if not os.path.exists(f'{os.getcwd()}/outputs'):
    os.makedirs(f'{os.getcwd()}/outputs')

# Define a file to log IceCream output
log_file_path = os.path.join(f'{os.getcwd()}/logs', f'{datetime.now().strftime("%Y-%m-%d-%H:%M:%S")}.log')

# Replace logging configuration with IceCream configuration
logger.configureOutput(prefix=' - ', outputFunction=lambda x: open(log_file_path, 'a').write(x + '\n'))


class DataReader(object):

    def __init__(self, data_paths):
        self.data_paths = data_paths
        
    def __iter__(self):
        for data_path in self.data_paths:
            name = os.path.split(data_path)[1]
            with open(data_path, 'r') as file:
                content = file.readlines()
                yield name, content

                
class XmlReader(object):

    def __init__(self, data_paths):
        self.data_paths = data_paths
        
    def __iter__(self):
        for data_path in self.data_paths:
            name = os.path.split(data_path)[1]
            with open(data_path, 'r') as file:
                yield name.replace('.xml', ''), ET.iterparse(file)


class JsonReader(object):

    def __init__(self, data_path):
        self.data_path = data_path
        
    def __iter__(self):
        with open(self.data_path, 'r') as file:
            entries = json.load(file)
            for entry in entries:
                yield entry


class JsonDataReader(object):
    
    def __init__(self, data_paths):
        self.data_paths = data_paths
        
    def __iter__(self):
        for data_path in self.data_paths:
            name = os.path.split(data_path)[1]
            if os.path.getsize(data_path) < 1:
                yield name, None
            else:
                with open(data_path, 'r') as file:
                    entries = json.load(file)
                    for entry in entries:
                        yield name, entry


def load_json_list(json_file):
    json_list = []
    for entry in JsonReader(json_file):
        json_list.append(entry)
    return json_list


def get_list_of_uniq_jsons(lst):
    uniq = []
    for new in lst:
        found = False
        for old in uniq:
            if new == old:
                found = True
                break
        if not found:
            uniq.append(new)
    return uniq


class PrettyDict(dict):

    def __str__(self):
        return "{" + ", ".join("%r: %r\n" % (key, self[key]) for key in sorted(self)) + "}"

    __repr__ = __str__


class ErrorproneMsg(object):
    
    keys = [' Proj',
            'Class',
            ' Type',
            '  Cat',
            '  Msg',
            ' Code',
            ' Mark',
            ' Line']

    def __init__(self, proj, cls, typ, cat, msg, code, mark, line):
        self.proj = proj
        self.cls = cls
        self.typ = typ
        self.cat = cat
        self.msg = msg
        self.code = code
        self.mark = mark
        self.line = int(line)
        self.values = [self.proj, self.cls, self.typ, self.cat,
                       self.msg, self.code, self.mark, self.line]

    def __str__(self):
        return("\n" + "\n".join(k + ": " + str(v) for (k, v) in zip(ErrorproneMsg.keys, self.values)) + "\n")

    __repr__ = __str__


class SpotbugsMsg(object):
    
    keys = ['    Proj',
            '   Class',
            '     Cat',
            '  Abbrev',
            '    Type',
            'Priority',
            '    Rank',
            '     Msg',
            '  Method',
            '   Field',
            '   Lines']
    
    def __init__(self, proj, cls, cat, abbrev, typ, prio, rank, msg, mth, field, lines):
        self.proj = proj
        self.cls = cls
        self.cat = cat
        self.abbrev = abbrev
        self.typ = typ
        self.prio = prio
        self.rank = rank
        self.msg = msg
        self.mth = mth
        self.field = field
        # lines could be list of tuples during serialization
        # or list of lists during deserialization
        # so construct namedtuples here instead of passing it from outside
        # so that it works during deserialization also.
        self.lines = []
        for l in lines:
            self.lines.append(SpotbugsSrcline(int(l[0]), int(l[1]), l[2]))
        self.values = [self.proj, self.cls, self.cat, self.abbrev, self.typ, self.prio,
                       self.rank, self.msg, self.mth, self.field, self.lines]
        
    def __str__(self):
        return("\n" + "\n".join(k + ": " + str(v) for (k, v) in zip(SpotbugsMsg.keys, self.values)) + "\n")

    __repr__ = __str__
    
    def unrollLines(self):
        lines = []
        for l in self.lines:
            lines.extend(range(l.start, l.end + 1))
        return list(set(lines))


SpotbugsSrcline = namedtuple('SpotbugsSrcline', ['start', 'end', 'role'])

'''
InferIssue and InferBugTrace are slightly modified to cope
with the new json format in Infer 0.15.0
'''
class InferIssue(object):
    # keys = ['bug_trace', 'bug_type', 'bug_type_hum', 'column', 'file', 'hash', 'key', 'line', 'node_key', 'procedure', 'procedure_start_line', 'qualifier', 'severity']
    keys = ['bug_trace', 'bug_type', 'bug_type_hum', 'column', 'file', 'hash', 'key', 'line', 'procedure', 'procedure_start_line', 'qualifier', 'severity']
    def __init__(self, bug_trace, bug_type, bug_type_hum, column, file, hash, key, line, procedure, procedure_start_line, qualifier, severity):
        self.bug_trace = []
        for t in bug_trace:
            self.bug_trace.append(InferBugTrace(*list(t[k] for k in InferBugTrace.keys)))
        self.bug_type = bug_type
        self.bug_type_hum = bug_type_hum
        self.column = column
        self.file = file
        self.hash = hash
        self.key = key
        self.line = line
        # self.node_key = node_key
        self.procedure = procedure
        self.procedure_start_line = procedure_start_line
        self.qualifier = qualifier
        self.severity = severity
        
        self.values = [self.bug_type, self.qualifier, self.severity, self.line, self.column, self.procedure, self.procedure_start_line, self.file, self.bug_trace, self.key, self.hash, self.bug_type_hum]
        
    def __str__(self):
        return("\n" + "\n".join(k + ": " + str(v) for (k, v) in zip(InferIssue.keys, self.values)) + "\n")
    
    __repr__ = __str__


class InferBugTrace(object):
    keys = ['level', 'filename', 'line_number', 'column_number', 'description']
    
#     def __init__(self, level, filename, line, column, desc, tags):
    def __init__(self, level, filename, line, column, desc):
        self.level = level
        self.filename = filename
        self.line = line
        self.column = column
        self.desc = desc
#         self.tags = tags
        
#         self.values = [self.level, self.filename, self.line, self.column, self.desc, self.tags]
        self.values = [self.level, self.filename, self.line, self.column, self.desc]
        
    def __str__(self):
        return("\n" + "\n".join(k + ": " + str(v) for (k, v) in zip(InferBugTrace.keys, self.values)) + "\n")
    
    __repr__ = __str__    


class InferMsg(object):
    keys = ['      Proj',
            '     Class',
            '  Bug_Type',
            '       Msg',
            '  Severity',
            '     Lines',
            ' Procedure']

    def __init__(self, proj, cls, bug_type, msg, severity, lines, procedure):
        self.proj = proj
        self.cls = cls
        self.bug_type = bug_type
        self.msg = msg
        self.severity = severity
        self.lines = lines
        self.procedure = procedure

        self.values = [self.proj, self.cls, self.bug_type, self.msg, self.severity, self.lines, self.procedure]
        
    def __str__(self):
        return("\n" + "\n".join(k + ": " + str(v) for (k, v) in zip(InferMsg.keys, self.values)))
    
    __repr__ = __str__


class FileDiff(object):

    keys = ['Project: ',
            '  Class: ',
            '  Lines: ']
    
    def __init__(self, proj, cls, lines):
        self.proj = proj
        self.cls = cls
        self.lines = set(int(i) for i in lines)
        self.values = [self.proj, self.cls, self.lines]

    def __str__(self):
        return("\n" + "\n".join(k + str(v) for (k, v) in zip(FileDiff.keys, self.values)) + "\n")

    __repr__ = __str__


class CustomEncoder(json.JSONEncoder):

    def default(self, o):
        if isinstance(o, ErrorproneMsg):
            return OrderedDict(zip(ErrorproneMsg.keys, o.values))
        elif isinstance(o, InferIssue):
            return OrderedDict(zip(InferIssue.keys, o.values))
        elif isinstance(o, InferMsg):
            return OrderedDict(zip(InferMsg.keys, o.values))
        elif isinstance(o, SpotbugsMsg):
            return OrderedDict(zip(SpotbugsMsg.keys, o.values))
        elif isinstance(o, FileDiff):
            return OrderedDict(zip(FileDiff.keys, o.values))
        elif isinstance(o, set):
            return list(o)
        else:
            json.JSONEncoder.default(self, o)


def load_parsed_diffs(diffs_file):
    diffs_ = []
    for diff in JsonReader(diffs_file):
        inst = FileDiff(*list(diff[k] for k in FileDiff.keys))
        diffs_.append(inst)
    return diffs_


def load_parsed_ep(ep_file):
    ep_res_ = []
    for msg in JsonReader(ep_file):
        inst = ErrorproneMsg(*list(msg[k] for k in ErrorproneMsg.keys))
        ep_res_.append(inst)
    return ep_res_


def load_parsed_sb(sb_file):
    sb_res_ = []
    for msg in JsonReader(sb_file):
        inst = SpotbugsMsg(*list(msg[k] for k in SpotbugsMsg.keys))
        sb_res_.append(inst)
    return sb_res_


def load_parsed_inf(inf_file):
    inf_res_ = []
    for msg in JsonReader(inf_file):
        inst = InferMsg(*list(msg[k] for k in InferMsg.keys))
        inf_res_.append(inst)
    return inf_res_


def find_msg_by_proj_and_cls(proj, cls, msgs):
    found_messages = []
    for m in msgs:
        if m.proj == proj and m.cls == cls:
            found_messages.append(m)
    return found_messages


LineMatchesToMessages = namedtuple('LineMatchesToMessages', ['lines', 'messages'])


def get_cls_name_from_file_path(cls_path):
    cls = None
    if '/com/' in cls_path:
        cls = 'com.' + cls_path.split('/com/')[1].replace('/', '.').replace('.java', '')
    elif '/org/' in cls_path:
        cls = 'org.' + cls_path.split('/org/')[1].replace('/', '.').replace('.java', '')
    return cls


def prepare_tool(root_dir):
    keyword = "SNAPSHOT.jar"
    found_files = []
    for root, dirs, files in os.walk(root_dir):
        for file in files:
            if keyword in file:
                found_files.append(os.path.join(root, file))
    return found_files

NO_WARNING = "NO_WARNING"

def copy_files(source_dir, destination_dir, paths_dict):
    for file_name, target_path in paths_dict.items():
        source_file = os.path.join(source_dir, file_name)
        destination_file = os.path.join(destination_dir, target_path)
        
        # Create directories if they don't exist
        os.makedirs(os.path.dirname(destination_file), exist_ok=True)
        
        # Copy the file
        shutil.copy2(source_file, destination_file)