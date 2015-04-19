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

class StrConvert(object):
    """Unicode Converter"""
    def __init__(self):
        pass

    @staticmethod
    def to_unicode(text):
        """To unicode"""
        if type(text).__name__ == 'unicode':
            return text

        elif type(text).__name__ == 'str':
            try:
                unicode_str = unicode(text, 'utf-8')
            except UnicodeDecodeError, err:
                try:
                    unicode_str = unicode(text, 'cp949')
                except UnicodeDecodeError, err:
                    try:
                        unicode_str = unicode(text, 'ascii')
                    except UnicodeDecodeError, err:
                        print u"Unicode decode error exception : %s" % err
                        sys.exit(2)
        return unicode_str

    @staticmethod
    def to_utf8(text):
        """To utf8 string"""
        if type(text).__name__ == 'unicode':
            return text.encode('utf-8')
        elif type(text).__name__ == 'str':
            return StrConvert.to_unicode(text).encode('utf-8')
        return text

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

    def __get_response_from_url(self, url_u, referer_u=""):
        """get response from url"""
        req = urllib2.Request(url_u)
        req.add_header("User-agent", self.user_agent)
        if len(referer_u) > 0:
            req.add_header("Referer", referer_u)
        response = urllib2.urlopen(req)
        return response.read()

    def get_title_board_urls_u(self, url):
        """get pair values(title, boardurl)"""
        contents = self.__get_response_from_url(url)
        compiled_regex = re.compile(
            r'<a href="(.*)" class="hx"[^>]+>\n\t+([^\t]+)\t+</a>', re.MULTILINE)
        regex_findall = compiled_regex.findall(contents)

        title_board_urls_u = []
        for regex_find in regex_findall:
            title_u = StrConvert.to_unicode(regex_find[1])
            board_url_u = StrConvert.to_unicode(regex_find[0])
            title_board_urls_u.append([title_u, board_url_u])
        return title_board_urls_u

    def get_title_board_urls_keywords_u(self, url_u, keywords_u, filters_u):
        """get unicode pair values(title, boardurl) with keywords"""
        title_board_urls_u = self.get_title_board_urls_u(url_u)

        filtered_title_board_urls_u = []
        for title_board_url_u in title_board_urls_u:
            if not any(filter_u in title_board_url_u[0].lower()
                       for filter_u in filters_u):
                filtered_title_board_urls_u.append(title_board_url_u)

        title_board_urls_keyword_u = []
        for filtered_title_board_url_u in filtered_title_board_urls_u:
            if any(keyword_u in filtered_title_board_url_u[0].lower()
                   for keyword_u in keywords_u):
                title_board_urls_keyword_u.append(filtered_title_board_url_u)

        return title_board_urls_keyword_u

    def __get_download_urls_u(self, url_u):
        """get torrent file downdload url"""
        contents = self.__get_response_from_url(url_u, url_u)
        regex_pattern = r'<td><a href="(.*)" target="_blank">' \
        r'<img src=".*"></a></td>'
        compiled_regex = re.compile(regex_pattern, re.MULTILINE)
        regex_findall = compiled_regex.findall(contents)
        download_urls_u = []
        for regex_find in regex_findall:
            download_urls_u.append(StrConvert.to_unicode(regex_find))
        return download_urls_u

    def get_torrent_download_urls_u(self, title_board_urls_u):
        """get pair values(title, download url)"""
        TorrentStraw.print_title_board_urls_u(title_board_urls_u)
        torrent_download_urls_u = []
        for title_boardurl_u in title_board_urls_u:
            (title_u, boardurl_u) = title_boardurl_u
            unescaped_download_urls = self.__get_unescaped_urls_u(
                self.__get_download_urls_u(boardurl_u))
            torrent_download_urls_u.append([title_u, unescaped_download_urls[0]])
        return torrent_download_urls_u

    @staticmethod
    def __get_unescape_u(text_u):
        """get unesace unicode html"""
        html_parser = htmllib.HTMLParser(None)
        html_parser.save_bgn()
        html_parser.feed(text_u)
        unescaped_u = html_parser.save_end()
        return unescaped_u

    @staticmethod
    def __get_unescaped_urls_u(urls_u):
        """get unescape unicode html string in url"""
        unescaped_urls_u = []
        for url_u in urls_u:
            unescaped_urls_u.append(TorrentStraw.__get_unescape_u(url_u))
        return unescaped_urls_u

    @staticmethod
    def pathname_to_url_utf8(pathname_u):
        """convert pathname to url"""
        pathname_utf8 = StrConvert.to_utf8(pathname_u)
        url_utf8 = urllib.pathname2url(pathname_utf8)
        return url_utf8.replace('///', '//')

    @staticmethod
    def download_torrent_file_u(title_download_url_u):
        """download torrent file"""
        (title_u, download_url_u) = title_download_url_u

        referer_url_u = "http://%s" % urllib2.urlparse.urlsplit(download_url_u).hostname
        request = urllib2.Request(download_url_u)
        request.add_header("Referer", referer_url_u)

        filename_u = '%s.torrent' % (title_u)
        temp_dir = tempfile.gettempdir()
        long_path_temp_dir_u = win32file.GetLongPathName(temp_dir)
        url_filename_utf8 = TorrentStraw.pathname_to_url_utf8(filename_u)
        write_file_path_u = os.path.join(long_path_temp_dir_u, url_filename_utf8)

        if os.path.isfile(write_file_path_u):
            print 'Already exist file.(%s)' % (write_file_path_u)
            return

        try:
            with open(write_file_path_u, "wb") as file_handle:
                file_handle.write(urllib2.urlopen(request).read())
        except IOError:
            print 'Could not save file.(%s)' % (write_file_path_u)
            return

        pathname_to_url_utf8 = TorrentStraw.pathname_to_url_utf8(long_path_temp_dir_u)
        url_path_utf8 = urllib2.urlparse.urlunparse(
            urllib2.urlparse.urlparse(pathname_to_url_utf8)._replace(scheme='file'))
        url_file_path_utf8 = urllib2.urlparse.urljoin(url_path_utf8 + '/', url_filename_utf8)

        return StrConvert.to_unicode(url_file_path_utf8)

    @staticmethod
    def download_torrent_files_u(title_download_urls_u):
        """download torrent file"""
        torrent_file_paths_u = []
        for title_download_url_u in title_download_urls_u:
            file_full_path_u = TorrentStraw.download_torrent_file_u(title_download_url_u)
            if file_full_path_u is not None:
                torrent_file_paths_u.append(file_full_path_u)
        return torrent_file_paths_u

    @staticmethod
    def print_title_board_urls_u(title_board_urls):
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

    def get_keywords_u(self):
        """get unicode keywords from parsed values"""
        keywords_u = []
        for keyword in self.parsed_values.keyword:
            keyword_u = StrConvert.to_unicode(keyword)
            keywords_u.append(keyword_u)
        return keywords_u

    def get_filters_u(self):
        """get unicode filters from parsed values"""
        filters_u = []
        for ignore_filter in self.parsed_values.filter:
            filter_u = StrConvert.to_unicode(ignore_filter)
            filters_u.append(filter_u)
        return filters_u

    def get_web_url_u(self):
        """get unicode web url from parser"""
        web_url_u = StrConvert.to_unicode(self.parsed_values.weburl)
        return web_url_u

    def get_ip_u(self):
        """get unicode ip address from parser"""
        ip_u = StrConvert.to_unicode(self.parsed_values.ip)
        return ip_u

    def get_port(self):
        """get port from parser"""
        port = StrConvert.to_unicode(self.parsed_values.port)
        return int(port)

    def get_username_u(self):
        """get unicode username from parser"""
        user_u = StrConvert.to_unicode(self.parsed_values.user)
        return user_u

    def get_password_u(self):
        """get unicode password from parser"""
        password_u = StrConvert.to_unicode(self.parsed_values.password)
        return password_u

def main():
    """main"""
    parser = CustomArgumentParser()
    if len(sys.argv) == 1:
        parser.parser.print_help()
        return

    web_url_u = parser.get_web_url_u()
    keywords_u = parser.get_keywords_u()
    filters_u = parser.get_filters_u()

    torrent_straw = TorrentStraw()
    title_board_urls_u = torrent_straw.get_title_board_urls_keywords_u(
        web_url_u, keywords_u, filters_u)

    torrent_title_download_urls_u = \
        torrent_straw.get_torrent_download_urls_u(title_board_urls_u)
    torrent_file_paths_u = torrent_straw.download_torrent_files_u(torrent_title_download_urls_u)

    if len(torrent_file_paths_u) == 0:
        print 'no result.'
        return

    u_ipaddress = parser.get_ip_u()
    port = parser.get_port()
    u_username = parser.get_username_u()
    u_password = parser.get_password_u()

    torrent_client = transmissionrpc.Client(
        address=u_ipaddress,
        port=port,
        user=u_username,
        password=u_password)

    for torrent_file_path_u in torrent_file_paths_u:
        torrent_object = torrent_client.add_torrent(torrent_file_path_u)
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
