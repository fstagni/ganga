from GangaTest.Framework.tests                     import GangaGPITestCase
from GangaDirac.Lib.Files.DiracFile                import DiracFile
#from GangaGaudi.Lib.RTHandlers.RunTimeHandlerUtils import get_share_path
#from Ganga.GPIDev.Adapters.StandardJobConfig       import StandardJobConfig
#from Ganga.Core.exceptions                         import ApplicationConfigurationError, GangaException
#from Ganga.GPI                                     import *
#import GangaDirac.Lib.Server.DiracServer as DiracServer
#GangaTest.Framework.utils defines some utility methods
#from GangaTest.Framework.utils import sleep_until_completed,sleep_until_state
import unittest, tempfile, os

class TestDiracFile(GangaGPITestCase):
    def setUp(self):
        from GangaDirac.Lib.Server.WorkerThreadPool import WorkerThreadPool
        class testServer(object):
            def __init__(this, returnObject):
                this.returnObject = returnObject
                this.toCheck      = {}

            def execute(this,command,timeout=60,env=None,cwd=None,shell=False):
                import inspect
                frame = inspect.currentframe()
                fedInVars = inspect.getargvalues(frame).locals
                del frame

                for key, value in this.toCheck.iteritems():
                    if key in fedInVars:
                        self.assertEqual(fedInVars[key], value)

                return this.returnObject
            def execute_nonblocking( this,command,command_args=(),command_kwargs={},timeout=60,env=None,cwd=None,shell=False,
                                     priority=5,callback_func=None,callback_args =(),callback_kwargs={} ):
                import inspect
                frame = inspect.currentframe()
                fedInVars = inspect.getargvalues(frame).locals
                del frame
                
                for key, value in this.toCheck.iteritems():
                    if key in fedInVars:
                        self.assertEqual(fedInVars[key], value)

                return this.returnObject
        self.df = DiracFile('np', 'ld', 'lfn')
        self.df.locations = ['location']
        self.df.guid      = 'guid'
        self.ts = testServer(None)
        setattr(WorkerThreadPool, "execute", self.ts.execute)
        setattr(WorkerThreadPool, "execute_nonblocking", self.ts.execute_nonblocking)
        #setattr(GangaDirac.Lib.Server.WorkerThreadPool, "WorkerThreadPool", )
        #setattr(GangaDirac.Lib.Backends.DiracBase, "ganga_dirac_server", self.ts)

    def test__init__(self):
        self.assertEqual(self.df.namePattern, 'np',  'namePattern not initialised as np')
        self.assertEqual(self.df.lfn,         'lfn', 'lfn not initialised as lfn')
        self.assertEqual(self.df.localDir,    'ld',  'localDir not initialised as ld')

        d1=DiracFile()
        self.assertEqual(d1.namePattern, '', 'namePattern not default initialised as empty')
        self.assertEqual(d1.lfn,         '', 'lfn not default initialised as empty')
        self.assertEqual(d1.localDir,    '', 'localDir not default initialised as empty')
        self.assertEqual(d1.locations,   [], 'locations not initialised as empty list')

        d2=DiracFile(namePattern='np', lfn='lfn', localDir='ld')
        self.assertEqual(d2.namePattern, 'np',  'namePattern not keyword initialised as np')
        self.assertEqual(d2.lfn,         'lfn', 'lfn not keyword initialised as lfn')
        self.assertEqual(d2.localDir,    'ld',  'localDir not keyword initialised as ld')
        
    def test__attribute_filter__set__(self):
        self.assertEqual(self.df._attribute_filter__set__('dummyAttribute',12), 12, 'Pass throught of non-specified attribute failed')
        self.assertEqual(self.df._attribute_filter__set__('lfn', 'a/whole/newlfn'), 'a/whole/newlfn', "setting of lfn didn't return the lfn value")
        self.assertEqual(self.df.namePattern, 'newlfn', "Setting the lfn didn't change the namePattern accordingly")
        self.assertEqual(self.df._attribute_filter__set__('localDir','~'), os.path.expanduser('~'), "Didn't fully expand the path")

    def test__on_attribute__set__(self):
        d1 = self.df._on_attribute__set__('','dummyAttrib')
        d2 = self.df._on_attribute__set__(Job()._impl,'outputfiles')
        self.assertEqual(d1, self.df, "didn't create a copy as default action")
        self.assertNotEqual(d2, self.df, "didn't modify properly when called with Job and outputfiles")
        self.assertEqual(d2.namePattern, self.df.namePattern, 'namePattern should be unchanged')
        self.assertEqual(d2.localDir, None, "localDir should be blanked")
        self.assertEqual(d2.lfn, '', "lfn should be blanked")

    def test__repr__(self):
        self.assertEqual(repr(self.df), "DiracFile(namePattern='%s', lfn='%s')" % (self.df.namePattern, self.df.lfn))

    def test__auto_remove(self):
        self.ts.toCheck={'command'  : 'removeFile("lfn")',
                         'shell'    : False,
                         'priority' : 7}
        self.assertEqual(self.df._auto_remove(), None)
        self.df.lfn=''
        self.assertEqual(self.df._auto_remove(), None)

    def test_remove(self):
        self.ts.toCheck={'command':'removeFile("lfn")'}
        self.ts.returnObject = {'OK': True, 'Value':{'Successful':{'lfn':True}}}
        self.assertEqual(self.df.remove(),  None)
        self.assertEqual(self.df.lfn,       '')
        self.assertEqual(self.df.locations, [])
        self.assertEqual(self.df.guid,      '')
        
        # Now lfn='' exception should be raised
        self.assertRaises(Exception, self.df.remove)

        self.df.lfn='lfn'

        fail_returns = [ ('Not Dict',                      'STRING!'),
                         ("No 'OK' present",               {'Value':{'Successful':{'lfn':True}}}),
                         ('OK is False',                   {'OK':False, 'Value':{'Successful':{'lfn':True}}}),
                         ("No 'Value' present",            {'OK':True}),
                         ("LFN not in Value['Successful']",{'OK':True, 'Value':{'Successful':{}}})
                         ]
        
        for label, fr in fail_returns:
            print "Testing failure when return is", label,'...',
            self.ts.returnObject = fr
            self.assertEqual(self.df.remove(), self.ts.returnObject)
            self.assertEqual(self.df.lfn, 'lfn')
            print "Pass"

    def test_replicate(self):
        from GangaDirac.Lib.Server.WorkerThreadPool import WorkerThreadPool

        def working_execute(this,command,timeout=60,env=None,cwd=None,shell=False):
            self.assertEqual(command, 'replicateFile("lfn", "DEST", "location")')
            return {'OK': True, 'Value':{'Successful':{'lfn':True}}}
        setattr(WorkerThreadPool, "execute", working_execute)        
        self.assertEqual(self.df.replicate('DEST'), None)
        self.assertEqual(self.df.locations, ['location', 'DEST'])

        def not_dict_execute(this,command,timeout=60,env=None,cwd=None,shell=False):
            self.assertEqual(command, 'replicateFile("lfn", "DEST", "location")')
            return 'STRING!'
        setattr(WorkerThreadPool, "execute", not_dict_execute)
        self.assertEqual(self.df.replicate('DEST'), 'STRING!')
 
        ret = {'Value':{'Successful':{'lfn':True}}}
        def no_ok_execute(this,command,timeout=60,env=None,cwd=None,shell=False):
            self.assertEqual(command, 'replicateFile("lfn", "DEST", "location")')
            return ret
        setattr(WorkerThreadPool, "execute", no_ok_execute)
        self.assertEqual(self.df.replicate('DEST'), ret)
  
        ret = {'OK':False, 'Value':{'Successful':{'lfn':True}}}
        def ok_false_execute(this,command,timeout=60,env=None,cwd=None,shell=False):
            self.assertEqual(command, 'replicateFile("lfn", "DEST", "location")')
            return ret
        setattr(WorkerThreadPool, "execute", ok_false_execute)
        self.assertEqual(self.df.replicate('DEST'), ret)
 
        ret = {'OK':True}
        def no_value_execute(this,command,timeout=60,env=None,cwd=None,shell=False):
            self.assertEqual(command, 'replicateFile("lfn", "DEST", "location")')
            return ret
        setattr(WorkerThreadPool, "execute", no_value_execute)
        self.assertEqual(self.df.replicate('DEST'), ret)
  
        ret = {'OK':True, 'Value':{'Successful':{}}}
        def no_lfn_execute(this,command,timeout=60,env=None,cwd=None,shell=False):
            self.assertEqual(command, 'replicateFile("lfn", "DEST", "location")')
            return ret
        setattr(WorkerThreadPool, "execute", no_lfn_execute)
        self.assertEqual(self.df.replicate('DEST'), ret)
          
        self.df.lfn=''
        self.assertRaises(Exception, self.df.replicate,'DEST')
        self.df.lfn='lfn'
        self.df.locations=[]
        self.assertRaises(Exception, self.df.replicate,'DEST')
        
    def test_get(self):
        import os
        from GangaDirac.Lib.Server.WorkerThreadPool import WorkerThreadPool
        
        self.assertRaises(Exception, self.df.get)
        self.df.localDir = os.getcwd()
        self.df.lfn=''
        self.assertRaises(Exception, self.df.get)
        self.df.lfn='lfn'
        
        def working_execute(this,command,timeout=60,env=None,cwd=None,shell=False):
            self.assertEqual(command, 'getFile("%s", destDir="%s")'%(self.df.lfn, self.df.localDir))
            return {'OK': True, 'Value':{'Successful':{'%s'%self.df.lfn:True}}}
        setattr(WorkerThreadPool, "execute", working_execute)        
        self.assertEqual(self.df.get(), None)
        
        self.df.lfn='/the/root/lfn'
        self.df.namePattern = ''
        self.assertEqual(self.df.get(), None)
        self.assertEqual(self.df.namePattern, 'lfn')
        
        self.df.lfn = '/the/root/lfn.gz'
        self.df.compressed = True
        self.df.namePattern=''
        self.assertEqual(self.df.get(), None)
        self.assertEqual(self.df.namePattern, 'lfn')


        def getMetadata(this):
            self.assertEqual(this, self.df)
            self.df.guid='guid'
            self.df.locations=['location']
        setattr(DiracFile, "getMetadata", getMetadata)
        self.df.guid=''
        self.assertEqual(self.df.get(), None)
        self.assertEqual(self.df.guid,'guid')
        self.assertEqual(self.df.locations,['location'])

        self.df.locations=[]
        self.assertEqual(self.df.get(), None)
        self.assertEqual(self.df.guid,'guid')
        self.assertEqual(self.df.locations,['location'])

        self.df.guid=''
        self.df.locations=[]
        self.assertEqual(self.df.get(), None)
        self.assertEqual(self.df.guid,'guid')
        self.assertEqual(self.df.locations,['location'])

        def not_dict_execute(this,command,timeout=60,env=None,cwd=None,shell=False):
            self.assertEqual(command, 'getFile("%s", destDir="%s")'%(self.df.lfn, self.df.localDir))
            return 'STRING!'
        setattr(WorkerThreadPool, "execute", not_dict_execute)
        self.assertEqual(self.df.get(), 'STRING!')
 
        ret = {'Value':{'Successful':{'lfn':True}}}
        def no_ok_execute(this,command,timeout=60,env=None,cwd=None,shell=False):
            self.assertEqual(command, 'getFile("%s", destDir="%s")'%(self.df.lfn, self.df.localDir))
            return ret
        setattr(WorkerThreadPool, "execute", no_ok_execute)
        self.assertEqual(self.df.get(), ret)
  
        ret = {'OK':False, 'Value':{'Successful':{'lfn':True}}}
        def ok_false_execute(this,command,timeout=60,env=None,cwd=None,shell=False):
            self.assertEqual(command, 'getFile("%s", destDir="%s")'%(self.df.lfn, self.df.localDir))
            return ret
        setattr(WorkerThreadPool, "execute", ok_false_execute)
        self.assertEqual(self.df.get(), ret)
 
        ret = {'OK':True}
        def no_value_execute(this,command,timeout=60,env=None,cwd=None,shell=False):
            self.assertEqual(command, 'getFile("%s", destDir="%s")'%(self.df.lfn, self.df.localDir))
            return ret
        setattr(WorkerThreadPool, "execute", no_value_execute)
        self.assertEqual(self.df.get(), ret)
  
        ret = {'OK':True, 'Value':{'Successful':{}}}
        def no_lfn_execute(this,command,timeout=60,env=None,cwd=None,shell=False):
            self.assertEqual(command, 'getFile("%s", destDir="%s")'%(self.df.lfn, self.df.localDir))
            return ret
        setattr(WorkerThreadPool, "execute", no_lfn_execute)
        self.assertEqual(self.df.get(), ret)

#    def test_tmp(self):
#        import os
#        #from GangaDirac.Lib.Backends.DiracBase import ganga_dirac_server
#        #print "HERE", ganga_dirac_server.__class__.__name__, dir(ganga_dirac_server)
#        self.df.localDir=os.getcwd()
#        self.ts.toCheck={'timeout':20}
#        self.assertEqual(self.df.get(),None)

