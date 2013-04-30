import webapp2
import logging
import traceback
import sys

#Format modules
import json
import yaml

import youtube_dl

class NoneFile(object):
    '''
    A file-like object that does nothing
    '''
    def write(self,msg):
        pass
    def flush(self,*args,**kaargs):
        pass
    def isatty(self):
        return False

class ScreenFile(NoneFile):
    def write(self,msg):
        logging.debug(msg)

if not hasattr(sys.stderr,'isatty'):
    #In GAE it's not defined and we must monkeypatch
    sys.stderr.isatty = lambda : False

class SimpleFileDownloader(youtube_dl.FileDownloader):
    def __init__(self,*args,**kargs):
        super(SimpleFileDownloader,self).__init__(*args,**kargs)
        self._screen_file=ScreenFile()
        self._ies = youtube_dl.gen_extractors()
        for ie in self._ies:
            ie.set_downloader(self)

def videos(url):
    '''
    Get a list with a dict for every video founded
    '''
    fd = SimpleFileDownloader({'outtmpl':'%(title)s'})
    res = fd.extract_info(url, download = False)#(url)
    r_type = res[0].get('_type', 'video')
    #Do not return yet playlists
    if r_type == 'video':
        videos = res
    elif r_type == 'playlist':
        videos = res[0]['entries']
    return videos

class Api(webapp2.RequestHandler):
    @property
    def out_format(self):
        """The format the response must use"""
        return self.request.get("format","json")
    @property
    def content_type(self):
        """Content type for the response"""
        if self.out_format == "json":
            return "application/json"
        if self.out_format == "yaml":
            return "application/yaml"
    def dumps(self,dic):
        """Dump a dic to a string using the format specified in the reques"""
        if self.out_format == "json":
            return json.dumps(dic)
        elif self.out_format == "yaml":
            return yaml.safe_dump(dic)
    def get(self):
        #Allow javascript get requests from other domains
        self.response.headers["Access-Control-Allow-Origin"] = "*"
        self.response.headers["Content-Type"] = self.content_type
        
        errors = (youtube_dl.DownloadError, youtube_dl.ExtractorError)
        try:
            url = self.request.get("url")
            vids = videos(url)
            dic = {'youtube-dl.version':youtube_dl.__version__,
                   'url':url,
                   'videos':vids}
        except errors as err:
            dic = {'error': str(err)}
            logging.error(traceback.format_exc())
        response = self.dumps(dic)
        self.response.out.write(response)