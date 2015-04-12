#-*- coding: utf-8 -*-
"""TorrentStraw"""

import os
import sys
import re
import urllib
import urllib2
import cookielib
import htmllib
import argparse
import tempfile
import win32file

import transmissionrpc


class TorrentStraw(object):
    """TorrentStraw class"""
    def __init__(self):
        """init"""
        self.user_agent = \
            '''Mozilla/4.0 (compatible; MSIE 8.0; Windows NT 5.1; Trident/4.0;
            .NET CLR 2.0.50727; .NET CLR 3.0.4506.2152; .NET CLR 3.5.30729)'''
        cookie_jar = cookielib.CookieJar()
        build_opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cookie_jar))
        urllib2.install_opener(build_opener)
        return

    def __get_response_from_url(self, url, referer=""):
        """get response from url"""
        req = urllib2.Request(url)
        req.add_header("User-agent", self.user_agent)
        if len(referer) > 0:
            req.add_header("Referer", referer)
        response = urllib2.urlopen(req)
        return response.read()

    @staticmethod
    def __utf8_to_unicode(pairs):
        """convert unicode to utf8"""
        unicode_pairs = []
        for pair in pairs:
            unicode_pairs.append([pair[0].decode(), pair[1].decode()])
        return unicode_pairs

    def get_title_board_urls(self, url):
        """get pair values(title, boardurl)"""
        contents = self.__get_response_from_url(url)
        compiled_regex = re.compile(
            r'<a href="(.*)" class="hx"[^>]+>\n\t+([^\t]+)\t+</a>', re.MULTILINE)
        board_url_titles = self.__utf8_to_unicode(compiled_regex.findall(contents))
        title_board_urls = []
        for board_url_title in board_url_titles:
            title_board_urls.append([board_url_title[1], board_url_title[0]])
        return title_board_urls

    def get_title_board_urls_keywords(self, url, unicode_keywords, unicode_filters):
        """get pair values(title, boardurl) with keywords"""
        title_board_urls = self.get_title_board_urls(url)

        filtered_title_board_urls = []
        for title_board_url in title_board_urls:
            for unicode_filter in unicode_filters:
                if unicode_filter not in title_board_url[0]:
                    filtered_title_board_urls.append(title_board_url)

        title_board_urls_with_keyword = []
        for title_board_url in filtered_title_board_urls:
            for unicode_keyword in unicode_keywords:
                if unicode_keyword in title_board_url[0]:
                    title_board_urls_with_keyword.append(title_board_url)

        return title_board_urls_with_keyword

    def __get_download_urls(self, url):
        """get torrent file downdload url"""
        contents = self.__get_response_from_url(url, url)
        regex_pattern = r'<td><a href="(.*)" target="_blank">' \
        r'<img src=".*"></a></td>'
        compiled_regex = re.compile(regex_pattern, re.MULTILINE)
        return compiled_regex.findall(contents)

    def get_torrent_title_download_urls(self, title_board_urls):
        """get pair values(title, download url)"""
        TorrentStraw.print_title_board_urls(title_board_urls)
        torrent_download_urls = []
        for title_boardurl in title_board_urls:
            (title, boardurl) = title_boardurl
            unescaped_download_urls = self.unescaped_urls(self.__get_download_urls(boardurl))
            torrent_download_urls.append([title, unescaped_download_urls[0]])
        return torrent_download_urls

    @staticmethod
    def unescape(text):
        """ remote html escape string"""
        html_parser = htmllib.HTMLParser(None)
        html_parser.save_bgn()
        html_parser.feed(text)
        return html_parser.save_end()

    @staticmethod
    def unescaped_urls(urls):
        """unescape html string in url"""
        unescaped_urls = []
        for url in urls:
            unescaped_urls.append(TorrentStraw.unescape(url))
        return unescaped_urls

    @staticmethod
    def pathname_to_url(pathname):
        """convert pathname to url"""
        utf8_pathname = pathname.encode('utf-8')
        utf8_url = urllib.pathname2url(utf8_pathname)
        return utf8_url.replace('///', '//')

    @staticmethod
    def download_torrent_file(title_download_url):
        """download torrent file"""
        (title, download_url) = title_download_url

        referer_url = "http://%s" % urllib2.urlparse.urlsplit(download_url).hostname
        request = urllib2.Request(download_url)
        request.add_header("Referer", referer_url)

        filename = '%s.torrent' % (title)
        temp_dir = tempfile.gettempdir()
        long_path_temp_dir = win32file.GetLongPathName(temp_dir)
        url_filename = TorrentStraw.pathname_to_url(filename)
        write_file_path = os.path.join(long_path_temp_dir, url_filename)

        if os.path.isfile(write_file_path):
            print 'Already exist file.(%s)' % (write_file_path)
            return

        try:
            with open(write_file_path, "wb") as file_handle:
                file_handle.write(urllib2.urlopen(request).read())
        except IOError:
            print 'Could not save file.(%s)' % (write_file_path)
            return

        pathname_to_url = TorrentStraw.pathname_to_url(long_path_temp_dir)
        url_path = urllib2.urlparse.urlunparse(
            urllib2.urlparse.urlparse(pathname_to_url)._replace(scheme='file'))
        url_file_path = urllib2.urlparse.urljoin(url_path + '/', url_filename)

        return url_file_path

    @staticmethod
    def download_torrent_files(title_download_urls):
        """download torrent file"""
        torrent_file_paths = []
        for title_download_url in title_download_urls:
            file_full_path = TorrentStraw.download_torrent_file(title_download_url)
            if file_full_path is not None:
                torrent_file_paths.append(file_full_path)
        return torrent_file_paths

    @staticmethod
    def print_title_board_urls(title_board_urls):
        """print pair values(title, boardurl)"""
        for title_board_url in title_board_urls:
            print "Title(%s), BoardUrl(%s)" % (title_board_url[0], title_board_url[1])


class CustomArgumentParser(object):
    """custom arguments parser"""
    def __init__(self):
        self.parser = argparse.ArgumentParser()
        self.parser.add_argument('--weburl', default='', help='torrent web board url')
        self.parser.add_argument('--keyword', nargs='+', default=[], help='torrent search keywords')
        self.parser.add_argument('--filter', nargs='+', default=[], help='except filters')
        self.parser.add_argument('--ip', default='', help='transmission ip address')
        self.parser.add_argument('--port', default=9091, help='transmission port')
        self.parser.add_argument('--user', default='', help='transmission user id')
        self.parser.add_argument('--password', default='', help='transmission user password')
        self.parsed_values = self.parser.parse_args()

    def get_keywords(self):
        """get unicode keywords from parsed values"""
        unicode_keywords = []
        for keyword in self.parsed_values.keyword:
            unicode_keyword = unicode(keyword, 'cp949')
            unicode_keywords.append(unicode_keyword)
        return unicode_keywords

    def get_filters(self):
        """get unicode filters from parsed values"""
        unicode_filters = []
        for ignore_filter in self.parsed_values.filter:
            unicode_filter = unicode(ignore_filter, 'cp949')
            unicode_filters.append(unicode_filter)
        return unicode_filters

    def get_web_url(self):
        """get web url from parser"""
        web_url = unicode(self.parsed_values.weburl, 'cp949')
        return str(web_url)

    def get_ip_address(self):
        """get ip address from parser"""
        ipaddress = unicode(self.parsed_values.ip, 'cp949')
        return str(ipaddress)

    def get_port(self):
        """get port from parser"""
        port = unicode(self.parsed_values.port, 'cp949')
        return int(port)

    def get_user(self):
        """get username from parser"""
        user = unicode(self.parsed_values.user, 'cp949')
        return str(user)

    def get_password(self):
        """get password from parser"""
        password = unicode(self.parsed_values.password, 'cp949')
        return str(password)

def main():
    """main"""
    parser = CustomArgumentParser()
    if len(sys.argv) == 1:
        parser.parser.print_help()
        return

    web_url = parser.get_web_url()
    unicode_keywords = parser.get_keywords()
    unicode_filters = parser.get_filters()

    torrent_straw = TorrentStraw()
    title_board_urls = torrent_straw.get_title_board_urls_keywords(
        web_url, unicode_keywords, unicode_filters)

    torrent_title_download_urls = \
        torrent_straw.get_torrent_title_download_urls(title_board_urls)
    torrent_file_paths = torrent_straw.download_torrent_files(torrent_title_download_urls)

    if len(torrent_file_paths) == 0:
        print 'no result.'
        return

    transmission_ip = parser.get_ip_address()
    transmission_port = parser.get_port()
    transmission_user = parser.get_user()
    transmission_password = parser.get_password()

    torrent_client = transmissionrpc.Client(
        address=transmission_ip,
        port=transmission_port,
        user=transmission_user,
        password=transmission_password)

    for torrent_file_path in torrent_file_paths:
        torrent_object = torrent_client.add_torrent(torrent_file_path)
        print "add_torrent name : %s" % (torrent_object.name)
    return


if __name__ == "__main__":
    reload(sys)
    sys.setdefaultencoding('utf-8')

    try:
        main()
    except os.error, err:
        print str(err)
        sys.exit(1)

    sys.exit(0)
