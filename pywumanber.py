# -*- coding: utf-8 -*-

# Copyright (c) 2011 Ciaran Farrell, Juergen Weigert
# All Rights Reserved.

# This program is free software; you can redistribute it and/ormodify
# it under the terms of version 2 of the GNU General Public License as
# published by the Free Software Foundation.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.   See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program; if not, see the followig website:
# https://www.gnu.org/licenses/old-licenses/gpl-2.0.txt

import os,urlparse,sys,time
from ctypes import *
from array import array
from urllib2 import urlopen,URLError,HTTPError,Request
WM_CALLBACK = CFUNCTYPE(c_int,c_int,c_int)

class WuManber:
  def __init__(self,keys,text,so='wumanber.so'):
    """ Initialise the WuManber object with required parameters
        Use __loadText__ and __loadKeywords__ to generate CTypes
        @keys:  list, string or filename
        @text:  string, url or filename
        @so:    name of the shared library linked to
    """
    from distutils.sysconfig import get_python_lib
    self.so = CDLL(os.path.join(get_python_lib(),so))
    self.keywords =  None
    self.clist_of_cstrings = None # NOT A PYTHON TYPE
    self.len_clist_of_strings = None # NOT A PYTHON TYPE
    self.ctext = None # NOT A PYTHON TYPE
    self.len_ctext = None # NOT A PYTHON TYPE
    self.text = None
    self.nocase = None # NOT A PYTHON TYPE
    self.wm = None # NOT A PYTHON TYPE
    self.keydict = {}
    self.__loadText__(text)
    self.__loadKeywords__(keys)
        
  def __loadText__(self,text):
    """ Parse the text provided by __init__. Depending on the type
        and whether the text is actually a URL, read the text into
        memory and create a CType c_char_p
        @text: string,url or filename
    """
    if os.path.exists(text):
      sys.stderr.write("loading text from existing file %s\n"%text)
      fd = open(text,'r')
      rawtext = fd.read()
      fd.close
      self.text = rawtext
      self.ctext = c_char_p(rawtext)
      self.len_ctext = c_int(len(rawtext))
    else:
      url = urlparse.urlparse(text)
      if url.scheme != '' and url.netloc != '':
        req = Request(url.geturl())
        try:
          response = urlopen(req)
        except URLError, e:
          raise
        except HTTPError,e:
          raise
        else:
          self.text = response.read()
          self.ctext = c_char_p(self.text)
          self.len_ctext = c_int(len(self.text)) # TODO: check validity of this!
      else:
        sys.stderr.write("Text not a file or url. Accepting it as such\n")
        self.ctext = c_char_p(text)
        self.len_ctext = c_int(len(text))
    
      
  def __loadKeywords__(self,keys):
    """ Depending on the type() of keys, first create a Python list of
        keywords and then convert that to a C array of CType c_char_p
        @keys:  list, string or filename
    """
    if isinstance(keys,list):
      sys.stderr.write("loading keywords from list\n")
      self.keywords = keys
    elif os.path.exists(keys):
        sys.stderr.write("loading keywords from file %s\n"%keys)
        try:
          fd = open(keys,'r')
        except IOError,e:
          raise "Could not open %s: %s"%(keys,str(e))
        else:
          self.keywords=[]
          for kw in fd.readlines():
            kw = kw.replace("\n","")
            if kw != "":
              self.keywords.append(kw)
        finally:
          if fd: fd.close()
    elif isinstance(keys,str):
      tmp = {}
      sys.stderr.write("loading keywords from str %s\n"%keys)
      kw = keys.split(",") # TODO: sanitize this?
      for k in kw:
        k = k.replace(",","")
        tmp[k] = None
      self.keywords = tmp.keys()      
    else:
      raise "wtf is %s?"%keys
    self.clist_of_cstrings = (c_char_p*(len(self.keywords)))()
    self.len_clist_of_strings = c_int(len(self.clist_of_cstrings))
    i = 0
    for pystring in self.keywords:
      self.clist_of_cstrings[i] = c_char_p(pystring)
      self.keydict[i] = []
      i+=1
        
  
  def __search_init__(self):
    """ Initialise the WuManber search by asking the shared library to
        prepare and return a WuManber struct. This struct is not actually
        used by this Python WuManber object or methods except to feed back
        into the shared library in the search_text method
    """
    if not self.clist_of_cstrings:
      raise StandardError,"CList of keywords not generated..."
    elif not self.len_clist_of_strings:
      raise StandardError,"CLength of keyword list not generated..."
    else:
      redundant_pointer = c_char_p('redundant')
      wm_ret = self.so.wm_search_init( self.clist_of_cstrings,
                                        self.len_clist_of_strings,
                                        self.nocase,
                                        redundant_pointer
                                      )
      wm_long = c_ulonglong(wm_ret)
      self.wm = wm_ret
      
  def __callback__(self,idx,ptr):
    """ This callback is called by the C shared library every time a match
        is found in the text to be searched. Read this method in conjunction
        with WM_CALLBACK which is defined at the beginning of this file
    """
    idx = idx-1 # C starts counting at 1?
    self.keydict[idx].append(ptr)
    return 0
      
  def search_text(self,nocase=True,verbose=False):
    """ search_text is responsible for actually performing the text search
        @nocase:  boolean, whether to use case sensitive searching or not
        @verbose  boolean, whether to use the callback to print results or not
        @returns: int, the number of matches found in the text
    """
    s = time.time()
    if nocase:
      self.nocase = c_int(1)
    else:
      self.nocase = c_int(0)
    self.__search_init__()
    null_ptr1,null_ptr2 = POINTER(c_int)(), POINTER(c_int)()
    if not verbose:
      cb = null_ptr1
    else:
      cb = WM_CALLBACK(self.__callback__)
    wm_ret = self.so.wm_search_text(self.wm,self.ctext,self.len_ctext,
      cb,null_ptr2)
    sys.stderr.write("search_text took %.2f seconds\n"%((time.time()-s)))
    return wm_ret
