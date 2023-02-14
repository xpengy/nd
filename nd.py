from typing import List, Optional, Tuple
import requests
import re
from bs4 import BeautifulSoup
from pathlib import Path
from io import BytesIO

BASE_PATH = Path.cwd()

# need to add your own cookies here

list_headers = {
    "cookie": "",
    "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36",
}

episode_headers = {
    "cookie": "",
    "accept": "application/json, text/javascript, */*; q=0.01",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36",
}


class NovelpiaDownloader:
    def __init__(self, novel_id: int):
        self.url = "https://novelpia.com"
        self.novel_id = novel_id

    def get_list_url(self):
        return f'{self.url}/proc/episode_list'

    def get_viewer_url(self, episode_id: int):
        return f'{self.url}/viewer/{episode_id}'

    def get_viewer_data_url(self, episode_id: int):
        return f'{self.url}/proc/viewer_data/{episode_id}'

    # returns response object
    def get_response(self, method: str, url: str, data: str, headers: dict[str, str]):
        return requests.request(method=method, url=url, data=data, headers=headers)

    # returns text of response object
    def get_text(self, method: str, url: str, data: str):
        return self.get_response(method, url, data, list_headers).text

    def get_json(self, method: str, url: str, data: str):
        return self.get_response(method, url, data, episode_headers).json()

    # returns page of episode list
    def get_episode_list(self, page: int):
        data = {"novel_no": self.novel_id, "page": page}
        return self.get_text("post", self.get_list_url(), data)

    # returns total pages for all episode list page
    def get_total_pages(self):
        regex = re.compile(
            rf"localStorage\['novel_page_{self.novel_id}'\] = '(.+?)'; episode_list\(\);"
        )
        html = self.get_episode_list(0)
        soup = BeautifulSoup(html, "lxml")
        page_link = soup.find_all("div", {"class": "page-link"})
        last_page = page_link[::-1][0]["onclick"]
        matched = regex.match(last_page)
        total_pages = matched.group(1)
        return int(total_pages), html

    # returns episode ids for each novel
    def get_episode_ids(self):
        episode_ids = []
        pages = []
        total_pages, page = self.get_total_pages()
        pages.append(page)

        for i in range(1, total_pages + 1):
            page = self.get_episode_list(i)
            pages.append(page)

        for page in pages:
            soup = BeautifulSoup(page, features="lxml")
            for episode_id in soup.find_all("i", {"class": "icon ion-bookmark"}):
                episode_ids.append(
                    int(episode_id["id"].replace("bookmark_", "")))

        return episode_ids

    # returns info and content of an episode
    def get_episode_data(self, ep_id: int):

        novel_info = self.get_text(
            "get", self.get_viewer_url(ep_id), "")

        soup_info = BeautifulSoup(novel_info, "lxml")

        ep_title = soup_info.find(
            "div", {"class": "menu-top-title"}).get_text(strip=True)
        ep_title = ep_title.replace("?", "？")

        ep_number = soup_info.find(
            "span", {"class": "menu-top-tag"}).get_text()

        nov_title = soup_info.find("title").get_text()
        cleaned_nov_title = re.sub(
            "노벨피아 - 웹소설로 꿈꾸는 세상! - ", "", nov_title)

        ep_data = self.get_json(
            "post", self.get_viewer_data_url(ep_id), "")

        return NovelEpisode(cleaned_nov_title, ep_title, ep_number, ep_id, ep_data)

    # downloads all episodes of novel
    def download_episode_all(self):
        episode_ids = self.get_episode_ids()
        for episode_id in episode_ids:
            print(episode_id)
            self.parse(self.get_episode_data(episode_id))

    # downloads an episode
    def download_episode(self, ep_id):
        self.parse(self.get_episode_data(ep_id))

    def parse(self, novel_data):
        buffer = BytesIO()
        for content in novel_data.content["s"]:
            text = content["text"]
            if "img" in text:
                soup = BeautifulSoup(text, "lxml")
                img = soup.find("img")
                src = img.attrs["src"]
                filename = img.get(
                    "data-filename") or img.get("id") or "cover.jpg"
                buffer.write(f"[{filename}]".encode("UTF-8"))
                self.download_img(filename, novel_data, src)
            else:
                buffer.write(
                    text.replace(
                        "&nbsp;", "\n").encode("UTF-8")
                )
        buffer.seek(0)
        self.download_novel(buffer, novel_data)

    def download_novel(self, buffer, novel_data):
        filename = f'{novel_data.episode_number}：{novel_data.episode_title}'
        folder = BASE_PATH / novel_data.novel_title
        folder.mkdir(exist_ok=True)

        with open(f'{str(folder)}\\{filename}.txt', "wb") as f:
            f.write(buffer.getvalue())

    def download_img(self, filename, novel_data, src):
        folder = BASE_PATH / novel_data.novel_title
        folder.mkdir(exist_ok=True)
        img_link = requests.get(f'https://{src[2:]}')

        with open(f'{str(folder)}\\{filename}.jpg', "wb") as f:
            f.write(img_link.content)


class NovelEpisode:
    def __init__(self, novel_title: str, episode_title: str, episode_number: int, episode_id: int, content):
        self.novel_title = novel_title
        self.episode_title = episode_title
        self.episode_number = episode_number
        self.episode_id = episode_id
        self.content = content


downloader = NovelpiaDownloader(93020)
downloader.download_episode_all()
# downloader.download_episode(1076989)
