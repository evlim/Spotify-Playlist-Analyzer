# -*- coding: utf-8 -*-
"""
Created on Sat Dec 12 04:21:31 2020

@author: Evan
"""

import re
import requests

class Request:
    def __init__(self, cookie_file: str = None, headers: dict = None, proxy: dict = None):
        if cookie_file is None:
            self.cookie = None
        else:
            self.cookie_file = cookie_file
            try:
                self.cookie = self._parse_cookie_file()
            except:
                raise

        if headers is None:
            self.headers = None
        else:
            self.headers = headers

        if proxy is None:
            self.proxy = None
        else:
            self.proxy = proxy

    def _parse_cookie_file(self) -> dict:
        """Parse a cookies.txt file and return a dictionary of key value pairs
        compatible with requests."""

        cookies = {}
        with open(self.cookie_file, 'r') as fp:
            for line in fp:
                if not re.match(r'^\#', line):
                    line_fields = line.strip().split('\t')
                    cookies[line_fields[5]] = line_fields[6]
        return cookies

    def request(self) -> requests.Session:
        """Create session using requests library and set cookie and headers."""

        request_session = requests.Session()
        if self.headers is not None:
            request_session.headers.update(self.headers)
        if self.cookie is not None:
            request_session.cookies.update(self.cookie)
        if self.proxy is not None:
            request_session.proxies.update(self.proxy)

        return request_session
    
#######################################################################################################
    
    

from requests.sessions import Session
from bs4 import BeautifulSoup
import yaml
import eyed3
import os
import logging

import json 
#import re
import ast

# Add json

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

formatter = logging.Formatter('%(levelname)s:%(asctime)s:%(module)s:%(lineno)d:%(name)s:%(message)s')

file_handler = logging.FileHandler('logfile_spotify_scraper.log')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

output_file = open('output.txt','w')
class Scraper:
    def __init__(self, session: Session, log: bool = False):
        self.session = session
        self.log = log

    @staticmethod
    def _str_to_json(string: str) -> dict:
        json_acceptable_string = string.replace('\n', '').strip()
        converted_string = yaml.load(json_acceptable_string, Loader=yaml.FullLoader)

        return converted_string

    @staticmethod
    def _ms_to_readable(millis: int) -> str:
        seconds = int(millis / 1000) % 60
        minutes = int(millis / (1000 * 60)) % 60
        hours = int(millis / (1000 * 60 * 60)) % 24
        if hours == 0:
            return "%d:%d" % (minutes, seconds)
        else:
            return "%d:%d:%d" % (hours, minutes, seconds)

    @staticmethod
    def _turn_url_to_embed(url: str) -> str:
        if 'embed' in url:
            return url
        else:
            return url.replace('/track/', '/embed/track/')

    def _image_downloader(self, url: str, file_name: str, path: str = '') -> str:
        request = self.session.get(url=url, stream=True)
        ext = request.headers['content-type'].split('/')[
            -1]  # converts response headers mime type to an extension (may not work with everything)
        if path == '':
            pass
        else:
            path = path + '//'
        file_name = "".join(x for x in file_name if x.isalnum())
        saving_directory = path + file_name + '.' + ext
        with open(saving_directory,
                  'wb') as f:  # open the file to write as binary - replace 'wb' with 'w' for text files
            for chunk in request.iter_content(1024):  # iterate on stream using 1KB packets
                f.write(chunk)  # write the file
        return saving_directory

    def _preview_mp3_downloader(self, url: str, file_name: str, path: str = '', with_cover: bool = False,
                                cover_url: str = '') -> str:
        if path == '':
            pass
        else:
            path = path + '//'

        file_name = file_name = "".join(x for x in file_name if x.isalnum())
        saving_directory = path + file_name + '.mp3'
        song = self.session.get(url=url, stream=True)
        with open(saving_directory, 'wb') as f:
            f.write(song.content)

        if with_cover:
            audio_file = eyed3.load(saving_directory)
            if audio_file.tag is None:
                audio_file.initTag()

            image_path = self._image_downloader(url=cover_url, file_name=file_name, path=path)
            audio_file.tag.images.set(3, open(image_path, 'rb').read(), 'image/')
            audio_file.tag.save()
            os.remove(path=image_path)

        return saving_directory

    def get_track_url_info(self, url: str) -> dict:
        try:
            page_content = self.session.get(url=self._turn_url_to_embed(url=url), stream=True).content
            try:
                bs_instance = BeautifulSoup(page_content, "lxml")
                url_information = self._str_to_json(string=bs_instance.find("script", {"id": "resource"}).contents[0])
                title = url_information['name']
                preview_mp3 = url_information['preview_url']
                duration = self._ms_to_readable(millis=int(url_information['duration_ms']))
                artist_name = url_information['artists'][0]['name']
                artist_url = url_information['artists'][0]['external_urls']['spotify']
                album_title = url_information['album']['name']
                album_cover_url = url_information['album']['images'][0]['url']
                album_cover_height = url_information['album']['images'][0]['height']
                album_cover_width = url_information['album']['images'][0]['width']
                release_date = url_information['album']['release_date']
                total_tracks = url_information['album']['total_tracks']
                type_ = url_information['album']['type']

                return {
                    'title': title,
                    'preview_mp3': preview_mp3,
                    'duration': duration,
                    'artist_name': artist_name,
                    'artist_url': artist_url,
                    'album_title': album_title,
                    'album_cover_url': album_cover_url,
                    'album_cover_height': album_cover_height,
                    'album_cover_width': album_cover_width,
                    'release_date': release_date,
                    'total_tracks': total_tracks,
                    'type_': type_,
                    'ERROR': None,
                }
            except Exception as error:
                if self.log:
                    logger.error(error)
                try:
                    bs_instance = BeautifulSoup(page_content, "lxml")
                    error = bs_instance.find('div', {'class': 'content'}).text
                    if "Sorry, couldn't find that." in error:
                        return {"ERROR": "The provided url doesn't belong to any song on Spotify."}
                except Exception as error:
                    if self.log:
                        logger.error(error)
                    return {"ERROR": "The provided url is malformed."}
        except:
            raise

    def download_cover(self, url: str, path: str = '') -> str:
        try:
            if 'playlist' in url:
                page_content = self.session.get(url=url, stream=True).content
                try:
                    bs_instance = BeautifulSoup(page_content, "lxml")
                    album_title = bs_instance.find('title').text
                    cover_url = bs_instance.find('meta', property='og:image')['content']
                    try:
                        return self._image_downloader(url=cover_url, file_name=album_title,
                                                      path=path)
                    except Exception as error:
                        if self.log:
                            logger.error(error)
                        return "Couldn't download the cover."

                except:
                    return "The provided url doesn't belong to any song on Spotify."



            else:
                page_content = self.session.get(url=self._turn_url_to_embed(url=url), stream=True).content
                try:
                    bs_instance = BeautifulSoup(page_content, "lxml")
                    url_information = self._str_to_json(
                        string=bs_instance.find("script", {"id": "resource"}).contents[0])
                    title = url_information['name']
                    album_title = url_information['album']['name']
                    album_cover_url = url_information['album']['images'][0]['url']

                    try:
                        return self._image_downloader(url=album_cover_url, file_name=title + '-' + album_title,
                                                      path=path)

                    except:
                        return "Couldn't download the cover."
                except:
                    try:
                        bs_instance = BeautifulSoup(page_content, "lxml")
                        error = bs_instance.find('div', {'class': 'content'}).text
                        if "Sorry, couldn't find that." in error:
                            return "The provided url doesn't belong to any song on Spotify."
                    except:
                        raise
        except:
            raise

    def download_preview_mp3(self, url: str, path: str = '', with_cover: bool = False) -> str:
        try:
            page_content = self.session.get(url=self._turn_url_to_embed(url=url), stream=True).content
            try:
                bs_instance = BeautifulSoup(page_content, "lxml")
                url_information = self._str_to_json(string=bs_instance.find("script", {"id": "resource"}).contents[0])
                title = url_information['name']
                album_title = url_information['album']['name']
                preview_mp3 = url_information['preview_url']
                album_cover_url = url_information['album']['images'][0]['url']

                try:
                    return self._preview_mp3_downloader(url=preview_mp3, file_name=title + '-' + album_title, path=path,
                                                        with_cover=with_cover, cover_url=album_cover_url)
                except Exception as error:
                    if self.log:
                        logger.error(error)
                    return "Couldn't download the cover."
            except:
                try:
                    bs_instance = BeautifulSoup(page_content, "lxml")
                    error = bs_instance.find('div', {'class': 'content'}).text
                    if "Sorry, couldn't find that." in error:
                        return "The provided url doesn't belong to any song on Spotify."
                except Exception as error:
                    if self.log:
                        logger.error(error)
                    raise
        except:
            raise

    def get_playlist_url_info(self, url: str) -> dict:
        try:
            if '?si' in url:
                url = url.split('?si')[0]
            page = self.session.get(url=url, stream=True).content
            
            #print(page)
            try:
                bs_instance = BeautifulSoup(page, "lxml")
                #bs_pretty = bs_instance.prettify()
                #output_file.write(bs_pretty)
                #print(bs_instance.prettify()) # show prettify
                
                tracks = bs_instance.find('ol', {'class': 'tracklist'})
                playlist_description = bs_instance.find('meta', {"name": "description"})['content']
                author_url = bs_instance.find('meta', property='music:creator')['content']
                author = author_url.split('/')[4]
                tracks_list = []
                album_title = bs_instance.find('title').text
                cover_url = bs_instance.find('meta', property='og:image')['content']
                temp_list = []
                counter = 0
                duration_list = tracks.find_all('span', {'class': 'total-duration'})
                #print(bs_instance.find_all('Spotify.Entity'))
                
                #print(bs_instance.find_all('script'))
                #print(bs_instance.find_all('script'))
                script_text = bs_instance.find_all('script')
                #output_file.write(script_text)
                #relevant = script_text[script_text.index('=')+1:] #removes = and the part before it
                #print(relevant)
                
                #print(script_text)
                
                #jsonData=json.loads(script_text)
                #print(jsonData)
                
                #tag = script_text.find_all('script')
                pattern = re.compile(r"\s+=\s+(\{.*\})")
                result = re.findall(pattern, str(script_text))[1]
                #print(result)
                
                json_data = json.loads(result)
                ##print(len(json_data))
                ##print(json_data)
                
                
                #zips = re.search(pattern, script_text)
                #print(json.loads(zips.group(0)))
                
                
                #data = json.loads(relevant) #a dictionary!
                #print(json.dumps(data))
                
                #x = ast.literal_eval(re.search('({.+})', str(script_text)).group(0))
                #print(x)
                #print(raw.find_all("Spotify.Entity"))
                for item in tracks.find_all('span', {"dir": "auto"}):
                    #print(item)
                    temp_list.append(item)
                    if len(temp_list) == 3:
                        try:
                            temp = {'track_name': temp_list[0].text, 'track_singer': temp_list[1].text,
                                    'track_album': temp_list[2].text,
                                    'duration': duration_list[counter].text, 'ERROR': None, }
                        except:
                            temp = {'track_name': temp_list[0].text, 'track_singer': temp_list[1].text,
                                    'track_album': temp_list[2].text,
                                    'duration': None, 'ERROR': None, }
                        tracks_list.append(temp)
                        temp_list = []
                        counter += 1

                data = {'album_title': album_title, 'cover_url': cover_url, 'author': author, 'author_url': author_url,
                        'playlist_description': playlist_description,
                        'tracks_list': tracks_list, 'ERROR': None, }
                #return data
                #return result
                return json_data
            except Exception as error:
                if self.log:
                    logger.error(error)
                return {"ERROR": "The provided url is malformed."}
        except:
            raise
            
            
            
            
            
            
            
            
            
# 
import pandas as pd # for Excel writing

# Create requests using Request which was imported before, You can also pass cookie_file, header and proxy inside Request(). 
# Default is None.
request = Request().request()

# Extract Spotify playlist information by URL
playlist_info = Scraper(session=request).get_playlist_url_info(url='https://open.spotify.com/playlist/37i9dQZF1DWTbzY5gOVvKd')
#print(type(playlist_info))

#playlist_name = playlist_info['album_title']

#output = pd.DataFrame(playlist_info['tracks_list'])
#output = pd.DataFrame(result)
#output = pd.DataFrame(playlist_info)
output = pd.json_normalize(playlist_info)

##print(output)


writer = pd.ExcelWriter('Playlist_Info.xlsx') # change playlist with a name that makes sense for the playlist
output.to_excel(writer, engine = 'xlsxwriter')
writer.save()
print("File saved in current directory and Playlist's name is \'", playlist_info, "\'.")
