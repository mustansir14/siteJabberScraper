FROM python:3.11.1-bullseye

WORKDIR /www

RUN apt-get update
RUN pip3 install --upgrade pip
RUN apt install -y wget curl gpg

RUN wget https://r.mariadb.com/downloads/mariadb_repo_setup
RUN chmod +x mariadb_repo_setup
RUN ./mariadb_repo_setup --mariadb-server-version="mariadb-10.9"

RUN apt install -y libmariadb3 libmariadb-dev
RUN apt install -y xvfb

RUN wget -qO - https://dl.google.com/linux/linux_signing_key.pub | gpg --dearmor -o /usr/share/keyrings/googlechrome-linux-keyring.gpg
RUN echo "deb [arch=amd64 signed-by=/usr/share/keyrings/googlechrome-linux-keyring.gpg] http://dl.google.com/linux/chrome/deb/ stable main" | tee /etc/apt/sources.list.d/google-chrome.list
RUN apt-get update && apt-get install -y google-chrome-stable

COPY ./install/requirements.txt ./install/requirements.txt
RUN pip3 install -r ./install/requirements.txt

COPY . /www

ENTRYPOINT [ "python3", "SiteJabberScraper.py", "--save_to_db=True", "--urls_from_file=urls.txt", "--no_of_threads=5" ]