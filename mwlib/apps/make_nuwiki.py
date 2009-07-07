
# Copyright (c) 2007-2009 PediaPress GmbH
# See README.txt for additional licensing information.

from mwlib.net import fetch, mwapi
from mwlib.metabook import get_licenses, parse_collection_page
from twisted.internet import reactor,  defer

class start_fetcher(object):
    def __init__(self, **kw):
        self.fetcher = None
        self.__dict__.update(kw)
        
    def get_api(self):
        api = mwapi.mwapi(self.api_url)
        if self.username:
            return api.login(self.username, self.password, self.domain)
        return defer.succeed(api)

    def fetch_pages_from_metabook(self,  api):
        fsout = self.fsout
        metabook=self.metabook
        
        fsout.dump_json(metabook=metabook)
        nfo = {
            'format': 'nuwiki',
            'base_url': self.base_url,
            'script_extension': self.options.script_extension,
        }
        if self.options.print_template_pattern:
            nfo["print_template_pattern"] = self.options.print_template_pattern

        fsout.dump_json(nfo=nfo)

        pages = fetch.pages_from_metabook(metabook)
        self.fetcher = fetch.fetcher(api, fsout, pages,
                                     licenses=self.licenses,
                                     status=self.status, 
                                     print_template_pattern=self.options.print_template_pattern,
                                     template_exclusion_category=self.options.template_exclusion_category,
                                     imagesize=self.options.imagesize)
        return self.fetcher.result
    
    def init_variables(self):
        base_url = self.base_url
        options = self.options
        
        if not base_url.endswith("/"):
            base_url += "/"
        api_url = "".join([base_url, "api", options.script_extension])
        if isinstance(api_url,  unicode):
            api_url = api_url.encode("utf-8")
        self.api_url = api_url

        self.username = options.username
        self.password = options.password
        self.domain   = options.domain
        
        self.fsout = fetch.fsoutput(self.fsdir)

    def fetch_collectionpage(self, api):
        if self.options.collectionpage is None:
            return api
        
        def got_pages(val):
            rawtext = val["pages"].values()[0]["revisions"][0]["*"]
            self.metabook = parse_collection_page(rawtext)
            return api
        return api.fetch_pages([self.options.collectionpage]).addBoth(got_pages)
        
    def run(self):
        self.init_variables()
        
        self.licenses = get_licenses(self.metabook)
        podclient = self.podclient
        if podclient is not None:
            old_class = podclient.__class__
            podclient.__class__ = fetch.PODClient

        def login_failed(res):
            print "Fatal error: login failed:", res.getErrorMessage()
            return res

        def reset_podclient(val):
            if podclient is not None:
                podclient.__class__ = old_class
            return val
        
        return (self.get_api()
                .addErrback(login_failed)
                .addCallback(self.fetch_collectionpage)
                .addCallback(self.fetch_pages_from_metabook)
                .addBoth(reset_podclient))

def make_nuwiki(fsdir, base_url, metabook, options, podclient=None, status=None):
    sf = start_fetcher(fsdir=fsdir, base_url=base_url, metabook=metabook, options=options, podclient=podclient, status=status)

    retval = []
    def done(val):
        retval.append(val)
        if val is None:
            print "done"
        else:
            print "done:",  val
            
        reactor.stop()

        
        
    reactor.callLater(0.0, lambda: sf.run().addBoth(done))
    reactor.run()
    import signal
    signal.signal(signal.SIGINT,  signal.SIG_DFL)
    signal.signal(signal.SIGTERM,  signal.SIG_DFL)
    
    if not retval:
        raise KeyboardInterrupt("interrupted")
            
    retval = retval[0]
    if retval is not None:
        raise RuntimeError(str(retval))
    
              
