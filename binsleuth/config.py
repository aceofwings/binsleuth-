from binsleuth.operations.bufferoverflow import BufferOverflowOperation
from binsleuth.operations.filemetadata import  FileMetaData
from binsleuth.operations.cfg import ControlFlowGraph
from binsleuth.operations.cve import CVEChecker

class Config(object):
    """
    Python config file for project. If no config file is present then this then
    framework will default to this
    """

    operations = [FileMetaData, ControlFlowGraph, BufferOverflowOperation, CVEChecker]

    """
    Can be a single string value or an array of string values
    representing file paths

    """
    file  = "./examples/fauxware"

    timeframe = 1

    function_graph_location = "function_graphs"

    loop_graph_location = ""
