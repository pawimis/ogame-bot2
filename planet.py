from config import options


class Planet(object):
    def __init__(self, id, name, coords, url, in_construction_mode=False, in_research_mode=False):
        self.id = id
        self.name = name
        self.url = url
        self.coords = coords
        self.mother = False
        self.galaxy, self.system, self.position = map(int, self.coords.split(":"))
        self.in_construction_mode = in_construction_mode
        self.in_research_mode = in_research_mode
        self.mines = (
            'metalMine',
            'crystalMine',
            'deuteriumMine'
        )
        self.researchesAll = ('energyTech', 'laserTech', 'ionTech', 'hyperspaceTech',
                             'plazmTech', 'fuelDrive', 'impulsDrive', 'hyperspaceDrive',
                             'spyTech', 'computerTech', 'astroPhysic', 'interstellarWeb',
                             'graviton', 'combatTech', 'defenceTech', 'armorTech')
        self.storage = {
            'metalStorage',
            'crystalStorage',
            'deuterStorage'
        }
        self.resources = {
            'metal': 0,
            'crystal': 0,
            'deuterium': 0,
            'energy': 0
        }
        self.storageBuildings = {
            'metalStorage': {
                'level': 0,
                'buildUrl': '',
                'can_build': False,
                'capacity': 0,
                'sufficient_energy': True
            },
            'crystalStorage': {
                'level': 0,
                'buildUrl': '',
                'can_build': False,
                'capacity': 0,
                'sufficient_energy': True
            },
            'deuterStorage': {
                'level': 0,
                'buildUrl': '',
                'can_build': False,
                'capacity': 0,
                'sufficient_energy': True
            }
        }
        self.buildings = {
            'metalMine': {
                'level': 0,
                'buildUrl': '',
                'can_build': False,
                'sufficient_energy': False
            },
            'crystalMine': {
                'level': 0,
                'buildUrl': '',
                'can_build': False,
                'sufficient_energy': False
            },
            'deuteriumMine': {
                'level': 0,
                'buildUrl': '',
                'can_build': False,
                'sufficient_energy': False
            },
            'solarPlant': {
                'level': 0,
                'buildUrl': '',
                'can_build': False,
                'sufficient_energy': True
            },
            'fusionPlant': {
                'level': 0,
                'buildUrl': '',
                'can_build': False,
                'sufficient_energy': True
            },
            'solarSatellite': {
                'level': 0,
                'buildUrl': '',
                'can_build': False,
                'sufficient_energy': True
            }
        }
        self.researches = {
            'energyTech': {
                'level': 0,
                'buildUrl': '',
                'can_build': False,
            },
            'laserTech': {
                'level': 0,
                'buildUrl': '',
                'can_build': False,
            },
            'ionTech': {
                'level': 0,
                'buildUrl': '',
                'can_build': False,
            },
            'hyperspaceTech': {
                'level': 0,
                'buildUrl': '',
                'can_build': False,
            },
            'plazmTech': {
                'level': 0,
                'buildUrl': '',
                'can_build': False,
            },
            'fuelDrive': {
                'level': 0,
                'buildUrl': '',
                'can_build': False,
            },
            'impulsDrive': {
                'level': 0,
                'buildUrl': '',
                'can_build': False,
            },
            'hyperspaceDrive': {
                'level': 0,
                'buildUrl': '',
                'can_build': False,
            },
            'spyTech': {
                'level': 0,
                'buildUrl': '',
                'can_build': False,
            },
            'computerTech': {
                'level': 0,
                'buildUrl': '',
                'can_build': False,
            },
            'astroPhysic': {
                'level': 0,
                'buildUrl': '',
                'can_build': False,
            },
            'interstellarWeb': {
                'level': 0,
                'buildUrl': '',
                'can_build': False,
            },
            'graviton': {
                'level': 0,
                'buildUrl': '',
                'can_build': False,
            },
            'combatTech': {
                'level': 0,
                'buildUrl': '',
                'can_build': False,
            },
            'defenceTech': {
                'level': 0,
                'buildUrl': '',
                'can_build': False,
            },
            'armorTech': {
                'level': 0,
                'buildUrl': '',
                'can_build': False,
            }
        }
        self.ships = {
            'lm': 0,
            'hm': 0,
            'cr': 0,
            'ow': 0,
            'pn': 0,
            'bb': 0,
            'ns': 0,
            'gs': 0,
            'lt': 0,
            'dt': 0,
            'cs': 0,
            'rc': 0,
            'ss': 0
        }

    def __str__(self):
        return self.name

    def __eq__(self, other):
        return self.id == other.id

    def get_mine_to_upgrade(self):
        build_options = options['building']
        levels_diff = map(int, build_options['levels_diff'].split(','))
        max_fusion_lvl = int(build_options['max_fusion_plant_level'])

        b = self.buildings
        stor = self.storageBuildings
        resource = self.resources
        build_power_plant = self.resources['energy'] <= 0

        mine_levels = [0, 0, 0]

        storage_cap = [0, 0, 0]

        resource_levels = [int(self.resources['metal']), int(self.resources['crystal']),
                           int(self.resources['deuterium'])]

        for k, s in enumerate(self.storage):
            storage_cap[k] = stor[s]['capacity']

        for i, mine in enumerate(self.mines):
            mine_levels[i] = b[mine]['level']

        for c in range(3):
            if storage_cap[c] <= resource_levels[c]:
                building = self.storage[c]
                return building, stor[building]['build_url']

        proposed_levels = [
            b['metalMine']['level'],
            b['metalMine']['level'] - levels_diff[0],
            b['metalMine']['level'] - levels_diff[0] - levels_diff[1]
        ]
        proposed_levels = [0 if l < 0 else l for l in proposed_levels]
        if proposed_levels == mine_levels or (
                mine_levels[1] >= proposed_levels[1] and mine_levels[2] >= proposed_levels[2]):
            proposed_levels[0] += 1

        num_suff_energy = 0
        for i in xrange(3):
            building = self.mines[i]
            if b[building]['sufficient_energy']:
                num_suff_energy += 1
            if b[building]['can_build'] and proposed_levels[i] > b[building]['level']:
                if b[building]['sufficient_energy']:
                    return building, b[building]['build_url']
                else:
                    build_power_plant = True

        if build_power_plant or num_suff_energy == 0:
            if b['solarPlant']['can_build']:
                return u'Solar plant', b['solarPlant']['build_url']
            elif b['fusionPlant']['can_build'] and \
                            b['fusionPlant']['level'] < max_fusion_lvl:
                return u'Fusion plant', b['fusionPlant']['build_url']
            else:
                return None, None
        else:
            return None, None

    def get_research_to_upgrade(self):
        research_options = options['reserch']
        queue = map(int, research_options['queue'].split(','))

        r = self.researches

        research_levels = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
        for i, res in enumerate(self.researchesAll):
            research_levels[i] = r[res]['level']

        research_priority_list = []
        for i in range(len(queue)):
            if queue[i] > 0:
                research_priority_list.append((self.researchesAll[i], queue[i]))

        research_priority_list = sorted(sorted(research_priority_list, key=lambda x: x[0]), key=lambda x: x[1], reverse=True)

        if len(research_priority_list) > 0:

            priority = [i[0] for i in research_priority_list]

            for p in priority:
                if r[p]['can_build']:
                    return p, r[p]['buildUrl']

        return None, None

    def is_moon(self):
        return False

    def has_ships(self):
        '''
        Return true if any ship is stationing on the planet
        '''
        return any(self.ships.values())

    def get_distance(self, planet):
        """
        Return distance to planet `planet`
        """
        try:
            g, s, p = map(int, planet.split(":"))
        except Exception:
            return 100000
        d = 0
        d += (abs(g - self.galaxy) * 100)
        d += (abs(s - self.system) * 10)
        d += (abs(p - self.position))

        return d

    def get_fleet_for_resources(self, r):
        total = sum([r.get('metal', 0), r.get('crystal', 0), r.get('deuterium', 0)])
        to_send = 0
        ships = {'dt': 0, 'lt': 0}
        for kind in ('dt', 'lt'):
            if self.ships[kind] > 0:
                for i in xrange(self.ships[kind]):
                    to_send += (25000 if kind == 'dt' else 5000)
                    ships[kind] += 1
                    if to_send > total:
                        return ships
        return ships

    def get_nearby_systems(self, radius):
        g, s, p = map(int, self.coords.split(":"))
        start_system = max(1, s - radius)
        end_system = min(499, s + radius)
        systems = []
        for system in xrange(start_system, end_system):
            systems.append("%s:%s" % (g, system))

        return systems


class Moon(Planet):
    def __init__(self, id, coords, url):
        super(Moon, self).__init__(id, 'Moon', coords, url)

    def get_mine_to_upgrade(self):
        return None, None

    def is_moon(self):
        return True

    def __str__(self):
        return '[%s] %s' % (self.coords, self.name)