import socket
import random
from BeautifulSoup import BeautifulSoup
from logging.handlers import RotatingFileHandler
import time
import logging
import mechanize
import os
import re
import sys
import signal
import math
from random import randint
from datetime import datetime, timedelta
from utils import *
from urllib import urlencode
from planet import Planet
from config import options
from transport_manager import TransportManager
from sim import Sim

socket.setdefaulttimeout(float(options['general']['timeout']))


class Bot(object):
    BASE_URL = 'http://pl.ogame.gameforge.com/'
    LOGIN_URL = 'http://pl.ogame.gameforge.com/main/login'
    HEADERS = [('User-agent', 'Mozilla/5.0 (X11; Linux x86_64; rv:45.0) Gecko/20100101 		Firefox/45.0')]
    RE_BUILD_REQUEST = re.compile(r"sendBuildRequest\(\'(.*)\', null, 1\)")
    RE_SERVER_TIME = re.compile(r"var serverTime=new Date\((.*)\);var localTime")
    LOGOUT_URL = 'https://s145-pl.ogame.gameforge.com/game/index.php?page=logout'

    def __init__(self, username=None, password=None, uni='145'):
        self.uni = uni
        self.username = username
        self.password = password
        self.logged_in = False

        self._prepare_logger()
        self._prepare_browser()

        self.MAIN_URL = 'https://s%s-pl.ogame.gameforge.com/game/index.php' % self.uni
        self.PAGES = {
            'main': self.MAIN_URL + '?page=overview',
            'resources': self.MAIN_URL + '?page=resources',
            'station': self.MAIN_URL + '?page=station',
            'research': self.MAIN_URL + '?page=research',
            'shipyard': self.MAIN_URL + '?page=shipyard',
            'defense': self.MAIN_URL + '?page=defense',
            'fleet': self.MAIN_URL + '?page=fleet1',
            'galaxy': self.MAIN_URL + '?page=galaxy',
            'galaxyCnt': self.MAIN_URL + '?page=galaxyContent',
            'events': self.MAIN_URL + '?page=eventList',
        }
        self.planets = []
        self.moons = []
        self.active_attacks = []

        self.fleet_slots = 0
        self.active_fleets = 0
        self.transport_manager = TransportManager()
        self.server_time = self.local_time = datetime.now()
        self.time_diff = 0
        self.sim = Sim()

    def _prepare_logger(self):
        self.logger = logging.getLogger("mechanize")
        fh = RotatingFileHandler('bot.log', maxBytes=100000, backupCount=5)
        sh = logging.StreamHandler()
        fmt = logging.Formatter(fmt='%(asctime)s %(levelname)s %(message)s',
                                datefmt='%m-%d, %H:%M:%S')
        fh.setFormatter(fmt)
        sh.setFormatter(fmt)
        self.logger.setLevel(logging.INFO)
        self.logger.addHandler(fh)
        self.logger.addHandler(sh)

    def _prepare_browser(self):
        self.br = mechanize.Browser()
        self.br.set_handle_equiv(True)
        self.br.set_handle_redirect(True)
        self.br.set_handle_referer(True)
        self.br.set_handle_robots(False)
        self.br.addheaders = self.HEADERS

    def login(self, username=None, password=None):
        username = username or self.username
        password = password or self.password

        try:
            resp = self.br.open(self.MAIN_URL, timeout=10)
            soup = BeautifulSoup(resp)
        except:
            return False

        alert = soup.find(id='attack_alert')

        # no redirect on main page == user logged in
        if resp.geturl() != self.BASE_URL and alert:
            self.logged_in = True
            self.logger.info('Logged as: %s' % username)
            return True

        self.logger.info('Logging in..')
        self.br.select_form(name='loginForm')
        self.br.form['uni'] = ['s%s-pl.ogame.gameforge.com' % self.uni]
        self.br.form['login'] = username
        self.br.form['pass'] = password
        self.br.submit()
        if self.br.geturl().startswith(self.MAIN_URL):
            self.logged_in = True
            self.logger.info('Logged as: %s' % username)
            return True
        else:
            self.logged_in = False
            self.logger.error('Login failed!')
            return False

    def fetch_planets(self):
        self.logger.info('Fetching planets..')
        resp = self.br.open(self.PAGES['main']).read()

        self.calc_time(resp)

        soup = BeautifulSoup(resp)
        self.planets = []
        self.moons = []

        try:
            for i, c in enumerate(soup.findAll('a', 'planetlink')):
                name = c.find('span', 'planet-name').text
                coords = c.find('span', 'planet-koords').text[1:-1]
                url = c.get('href')
                p_id = int(c.parent.get('id').split('-')[1])
                construct_mode = len(c.parent.findAll('a', 'constructionIcon')) != 0
                p = Planet(p_id, name, coords, url, construct_mode)
                if i == 0:
                    p.mother = True
                self.planets.append(p)
                time.sleep(3)

                # check if planet has moon
                # moon = c.parent.find('a', 'moonlink')
                # if moon and 'moonlink' in moon['class']:
                #	url = moon.get('href')
                #	m_id = url.split('cp=')[1]
                #	m = Moon(m_id, coords, url)
                #	self.moons.append(m)
        except:
            self.logger.exception('Exception while fetching planets')
        else:
            self.check_attacks(soup)

    def sleep(self):
        sleep_options = options['general']
        sleep_time = randint(0, int(sleep_options['seed'])) + int(sleep_options['check_interval'])
        self.logger.info('Sleeping for %s secs' % sleep_time)
        if self.active_attacks:
            sleep_time = 60
        time.sleep(sleep_time)

    def handle_planets(self):
        self.fetch_planets()

        for p in iter(self.planets):
            if p.mother:
                self.update_planet_laboratory(self,p)
                time.sleep(randint(2, 8))
            self.update_planet_info(p)
            time.sleep(randint(2, 8))
            # self.update_planet_fleet(p)
            # for m in iter(self.moons):
            #	self.update_planet_info(m)
            #	self.update_planet_fleet(m)

    def update_planet_fleet(self, planet):
        resp = self.br.open(self._get_url('fleet', planet))
        soup = BeautifulSoup(resp)
        ships = {}
        for k, v in self.SHIPS.iteritems():
            available = 0
            try:
                s = soup.find(id='button' + v)
                available = int(s.find('span', 'textlabel').nextSibling.replace('.', ''))
            except:
                available = 0
            ships[k] = available

        # self.logger.info('Updating %s fleet' % planet)
        # self.logger.info('%s' % fleet)
        planet.ships = ships

    def update_planet_info(self, planet):
        in_construction_mode = False
        resp = self.br.open(self._get_url('resources', planet))
        soup = BeautifulSoup(resp)
        time.sleep(randint(3, 15))

        try:
            metal = int(soup.find(id='resources_metal').text.replace('.', ''))
            planet.resources['metal'] = metal
            crystal = int(soup.find(id='resources_crystal').text.replace('.', ''))
            planet.resources['crystal'] = crystal
            deuterium = int(soup.find(id='resources_deuterium').text.replace('.', ''))
            planet.resources['deuterium'] = deuterium
            energy = int(soup.find(id='resources_energy').text.replace('.', ''))
            planet.resources['energy'] = energy
        except:
            self.logger.exception('Exception while updating resources info')
        else:
            self.logger.info('Updating resources info for %s:' % planet)
            s = 'metal - %(metal)s, crystal - %(crystal)s, deuterium - %(deuterium)s'
            self.logger.info(s % planet.resources)
        if planet.is_moon():
            return
        try:
            buildingList = soup.find(id='building')
            buildings = ('metalMine', 'crystalMine', 'deuteriumMine', 'solarPlant',
                         'fusionPlant', 'solarSatellite')
            for building, b in zip(buildings, buildingList.findAll('li')):
                can_build = 'on' in b.get('class')
                fb = b.find('a', 'fastBuild')
                build_url = fb.get('onclick') if fb else ''
                if build_url:
                    build_url = self._parse_build_url(build_url)
                try:
                    level = int(b.find('span', 'textlabel').nextSibling)
                except AttributeError:
                    try:
                        level = int(b.find('span', 'level').text)
                    except:
                        pass
                suff_energy = planet.resources['energy'] - self.sim.upgrade_energy_cost(building, level + 1) > 0
                res = dict(
                    level=level,
                    can_build=can_build,
                    build_url=build_url,
                    sufficient_energy=suff_energy
                )

                planet.buildings[building] = res
            storageList = soup.find(id='storage')
            storages = ('metalStorage', 'crystalStorage', 'deuterStorage')
            for storage, s in zip(storages, storageList.findAll('li')):
                can_build = 'on' in s.get('class')
                fb = s.find('a', 'fastBuild')
                build_url = fb.get('onclick') if fb else ''
                if build_url:
                    build_url = self._parse_build_url(build_url)
                try:
                    level = int(s.find('span', 'textlabel').nextSibling)
                    capacity = int(float(int(12.5 * math.exp(20 * float(level) / 33)) / 5) * 5 * 1000)
                    print level
                    print capacity

                except AttributeError:
                    try:
                        level = int(s.find('span', 'level').text)
                    except:
                        pass
                suff_energy = 0
                res = dict(
                    level=level,
                    build_url=build_url,
                    can_build=can_build,
                    capacity=capacity,
                    sufficient_energy=suff_energy
                )
                planet.storageBuildings[storage] = res

            if buildingList.find('div', 'construction'):
                in_construction_mode = True
            if storageList.find('div', 'construction'):
                in_construction_mode = True
        except:
            self.logger.exception('Exception while updating buildings info')
            return False
        else:
            self.logger.info('%s buildings were updated' % planet)
        if not in_construction_mode:
            text, url = planet.get_mine_to_upgrade()
            if url:
                self.logger.info('Building upgrade on %s: %s' % (planet, text))
                self.br.open(url)
                planet.in_construction_mode = True
                # let now transport manager to clear building queue
                self.transport_manager.update_building(planet)
                time.sleep(randint(5, 15))
            else:
                return False
        else:
            self.logger.info('Building queue is not empty')
        return True

    def update_planet_laboratory(self, planet):
        in_research_mode = False
        resp = self.br.open(self._get_url('research', planet))
        soup = BeautifulSoup(resp)
        time.sleep(randint(3, 15))
        if planet.is_moon():
            return

        try:
            researchList = soup.find(id='base1')
            researches = ('energyTech', 'laserTech', 'ionTech', 'plazmTech',
                         'fuelDrive', 'impulsDrive', 'hyperspaceDrive', 'spyTech',
                         'computerTech', 'astroPhysic', 'interstellarWeb', 'hyperspaceTech',
                         'combatTech', 'defenceTech', 'armorTech')
            for research, r in zip(researches, researchList.findAll('li')):
                can_build = 'on' in r.get('class')
                fb = r.find('a', 'fastBuild')
                build_url = fb.get('onclick') if fb else ''
                if build_url:
                    build_url = self._parse_build_url(build_url)
                try:
                    level = int(r.find('span', 'textlabel').nextSibling)
                except AttributeError:
                    try:
                        level = int(r.find('span', 'level').text)
                    except:
                        pass
                res = dict(
                    level=level,
                    can_build=can_build,
                    build_url=build_url,
                )

                planet.reserches[researches] = res
            if researchList.find('div', 'construction'):
                in_research_mode = True
        except:
            self.logger.exception('Exception while updating buildings info')
            return False
        else:
            self.logger.info('%s researches were updated' % planet)
        if not in_research_mode:
            text, url = planet.get_reserch_to_upgrade()
            if url:
                self.logger.info('Research upgrade on %s: %s' % (planet, text))
                self.br.open(url)
                planet.in_research_mode = True
                # let now transport manager to clear building queue
                self.transport_manager.update_research(planet)
                time.sleep(randint(5, 15))
            else:
                return False
        else:
            self.logger.info('Building queue is not empty')
        return True

    def _parse_build_url(self, js):
        """
        convert: `sendBuildRequest('url', null, 1)`; into: `url`
        """
        return self.RE_BUILD_REQUEST.findall(js)[0]

    def calc_time(self, resp):
        try:
            y, mo, d, h, mi, sec = map(int, self._parse_server_time(resp).split(','))
        except:
            self.logger.error('Exception while calculating time')
        else:
            self.local_time = n = datetime.now()
            self.server_time = datetime(n.year, n.month, n.day, h, mi, sec)
            self.time_diff = self.server_time - self.local_time

            self.logger.info('Server time: %s, local time: %s' % \
                             (self.server_time, self.local_time))

    def check_attacks(self, soup):
        alert = soup.find(id='attack_alert')
        if not alert:
            self.logger.exception('Check attack failed')
            return
        if 'noAttack' in alert.get('class', ''):
            self.logger.info('No attacks')
            self.active_attacks = []
        else:
            self.logger.info('ATTACK!')

    def _get_url(self, page, planet=None):
        url = self.PAGES[page]
        if planet is not None:
            url += '&cp=%s' % planet.id
        return url

    def start(self):
        self.logger.info('Starting bot')
        self.pid = str(os.getpid())
        self.pidfile = 'bot.pid'
        file(self.pidfile, 'w').write(self.pid)
        while True:
            if self.login():
                try:
                    self.handle_planets()
                except Exception as e:
                    self.logger.exception(e)
                    break
            else:
                self.logger.error('Login failed!')
                break
            self.sleep()
        resp = self.br.open(self.MAIN_URL, timeout=10)
        self.logger.info('LOGOUT')
        quit()

    def exit_gracefully(self, signum, frame):
        signal.signal(signal.SIGINT, original_sigint)
        resp = self.br.open(self.MAIN_URL, timeout=10)
        print('LOGOUT with break')
        quit()


if __name__ == "__main__":
    credentials = options['credentials']
    bot = Bot(credentials['username'], credentials['password'], credentials['uni'])
    original_sigint = signal.getsignal(signal.SIGINT)
    signal.signal(signal.SIGINT, bot.exit_gracefully)
    bot.start()
