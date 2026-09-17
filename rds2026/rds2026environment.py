#!/usr/bin/pyton
# encoding: utf-8

import runpy, os, sys, pygame

TILE_SIZE = 20

TILE_WALL = 0
TILE_WALL_WINDOW_V, TILE_WALL_WINDOW_H = 1, 2
TILE_WINDOW_V, TILE_WINDOW_H = 3, 4
TILE_DOOR_V, TILE_DOOR_H, TILE_RECHARGE = 5, 6, 7
TILE_UNKNOWN_OBJ = -1

TILE_IMAGES = {
    TILE_WALL: 'img/wall.png',
    TILE_WALL_WINDOW_V: 'img/wall_window_v.png',
    TILE_WALL_WINDOW_H: 'img/wall_window_h.png',
    TILE_WINDOW_V: 'img/window_v.png',
    TILE_WINDOW_H: 'img/window_h.png',
    TILE_DOOR_V: 'img/door_v.png',
    TILE_DOOR_H: 'img/door_h.png',
    TILE_RECHARGE: 'img/recharge.png',
}

class floorplan():

    screen = None
    size = None
    objects = []
    extra_objects = {
        'under': [],
        'above': []
    }
    recharge_tiles = []

    cfg_obj_walls = []
    cfg_obj_objects = []

    def __init__(self, config_file):
        n_rows = 0
        n_cols = 0
        
        # read config
        if not os.path.isfile(config_file):
            print("ERROR: no config file '{}' found!".format(config_file))
            sys.exit(1)
        cfg_file_data = runpy.run_path(config_file)

        # check walls
        if not 'walls' in cfg_file_data:
            print("ERROR: format error in config file! no walls")
            sys.exit(1)

        # read walls
        for r in cfg_file_data['walls']:
            r_col = 0
            for c in r.rstrip():
                r_col += 1
                if c == '#':
                    self.cfg_obj_walls.append({'x':r_col-1, 'y':n_rows,
                        'id':TILE_WALL})
                elif c == '|':
                    self.cfg_obj_walls.append({'x':r_col-1, 'y':n_rows,
                        'id':TILE_WALL_WINDOW_V})
                elif c == '-' or c == "=":
                    self.cfg_obj_walls.append({'x':r_col-1, 'y':n_rows,
                        'id':TILE_WALL_WINDOW_H})
                elif c == 'W':
                    self.cfg_obj_walls.append({'x':r_col-1, 'y':n_rows,
                        'id':TILE_WINDOW_V})
                elif c == 'w':
                    self.cfg_obj_walls.append({'x':r_col-1, 'y':n_rows,
                        'id':TILE_WINDOW_H})
                elif c == 'D':
                    self.cfg_obj_walls.append({'x':r_col-1, 'y':n_rows,
                        'id':TILE_DOOR_V})
                elif c == 'd':
                    self.cfg_obj_walls.append({'x':r_col-1, 'y':n_rows,
                        'id':TILE_DOOR_H})
                elif c == 'R':
                    self.cfg_obj_walls.append({'x':r_col-1, 'y':n_rows,
                        'id':TILE_RECHARGE})
                else:
                    continue
            if r_col > n_cols:
                n_cols = r_col
            n_rows += 1

        # read objects
        if 'objects' in cfg_file_data:
            for obj in cfg_file_data['objects']:
                obj['id'] = TILE_UNKNOWN_OBJ
                self.cfg_obj_objects.append(obj)

        # size based en cols and rows
        self.size = (n_cols, n_rows)
    
    def init_images(self, screen):
        self.screen = screen
        dd = screen['window']['density']
        coordinates = (0, 0)
        m, n = 0, 0
        
        # update walls
        n = 0
        for obj in self.cfg_obj_walls:
            img = pygame.transform.scale(
                pygame.image.load(TILE_IMAGES[obj['id']]), (dd, dd)
            )
            rect_img = img.get_rect()
            rect_img.x = obj['x'] * dd
            rect_img.y = obj['y'] * dd
            if obj['id'] == TILE_RECHARGE:
                self.recharge_tiles.append((obj['x'], obj['y']))
                # remember: later recharge tiles MUST be added in level -1
            else:
                self.objects.append({'img':img,
                    'bbox':rect_img.copy(), 'desc':'wall'})
            # update
            n += 1

        # max, min levels
        min_level = -1
        max_level = 0
        for obj in self.cfg_obj_objects:
            if 'level' in obj:
                min_level = min(min_level, obj['level'])
                max_level = max(max_level, obj['level'])
        
        # update objects, no walls
        n = 0
        for i in range(min_level, max_level+1):
            if i == -1:
                # do you remember the rechargable tiles? add them!
                for obj in self.recharge_tiles:
                    img = pygame.transform.scale(
                        pygame.image.load(TILE_IMAGES[TILE_RECHARGE]), (dd, dd)
                    )
                    rect_img = img.get_rect()
                    rect_img.x = obj[0] * dd
                    rect_img.y = obj[1] * dd
                    self.extra_objects['under'].append({'img':img, 'bbox':rect_img.copy(),
                        'desc':'recharge', 'level':-1})
            for obj in self.cfg_obj_objects:
                # prepare img
                level = 0
                if 'level' in obj:
                    level = obj['level']
                if not 'file' in obj:
                    print("ERROR: format error for object #{} in config file: no file info".format(n))
                    sys.exit(1)
                original_img_load = pygame.image.load(obj['file'])
                original_img_rect = original_img_load.get_rect()
                img = pygame.transform.scale(
                    original_img_load, (
                        int(original_img_rect.width/TILE_SIZE * dd),
                        int(original_img_rect.height/TILE_SIZE * dd)
                    )
                )
                rect_img = img.get_rect()
                if not 'coord' in obj:
                    print("ERROR: format error for object #{} in config file: no coordinates info".format(n))
                    sys.exit(1)
                else:
                    rect_img.x = (obj['coord'][0] - original_img_rect.width/TILE_SIZE//2) * dd
                    rect_img.y = (obj['coord'][1] - original_img_rect.height/TILE_SIZE//2) * dd

                    # level 0: objects
                    if level == 0:
                        self.objects.append({'img':img, 'bbox':rect_img.copy(),
                            'desc':obj['desc']})
                    # another level: objects
                    else:
                        if level < 0:
                            self.extra_objects['under'].append({'img':img, 'bbox':rect_img.copy(),
                                'desc':obj['desc'], 'level':level})
                        else:
                            self.extra_objects['above'].append({'img':img, 'bbox':rect_img.copy(),
                                'desc':obj['desc'], 'level':level})
                # update
                n += 1
        # clean
        self.cfg_obj_walls = []
        self.cfg_obj_objects = []

    def update(self):
        self.screen['display'].fill((200, 200, 200))
        # under
        for obj in self.extra_objects['under']:
                self.screen['display'].blit(obj['img'], obj['bbox'])
        # collision objets
        for obj in self.objects:
            self.screen['display'].blit(obj['img'], obj['bbox'])
            if self.screen['debugging']:
                if obj['desc'] == 'wall': continue
                pygame.draw.rect(self.screen['display'], (100, 100, 200), obj['bbox'], 2)

    def update_extra(self):
        # above
        for obj in self.extra_objects['above']:
            self.screen['display'].blit(obj['img'], obj['bbox'])

