#
#
# Copyright (C) University of Melbourne 2012
#
#
#
#Permission is hereby granted, free of charge, to any person obtaining a copy
#of this software and associated documentation files (the "Software"), to deal
#in the Software without restriction, including without limitation the rights
#to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#copies of the Software, and to permit persons to whom the Software is
#furnished to do so, subject to the following conditions:
#
#The above copyright notice and this permission notice shall be included in all
#copies or substantial portions of the Software.
#
#THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
#OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
#SOFTWARE.
#
#

from tools import mureilbuilder, mureilexception

import sys
import logging

logger = logging.getLogger(__name__)

def rungedemo(flags, input_data):
    master = None
    results = None

    # This section constructs the master, and does not depend on
    # the input_data from the web interface.
    try:
        master = mureilbuilder.build_master(flags)
    except mureilexception.MureilException as me:
        handle_exception(me)

    # master.run(input_data) completes all the processing required
    # on a single request, with output into the 'results' variable.
    # A server-type setup where the master was only constructed once
    # (and hence the timeseries data read in only once) would call 
    # results = master.run(input_data) for each request.
    if master:    
        try:
            results = master.run(input_data)
        except mureilexception.MureilException as me:
            handle_exception(me)
        except Exception as me:
            logger.critical('Execution stopped on unhandled exception',
                exc_info=me)
        finally:
            master.finalise()
    
    return results
    

def handle_exception(me):
    # More information than this is available in the exception
    logger.critical('Execution stopped on ' + me.__class__.__name__)
    logger.critical(me.msg)


if __name__ == '__main__':
    rungedemo(sys.argv[1:])
