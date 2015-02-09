#!/usr/bin/env python
# -*- coding: utf-8 -*-
# ---------------------------------------------------------------------------
#  - Author:    desko27
#  - Email:     desko27@gmail.com
#  - Version:   1.1.2
#  - Created:   2015/01/28
#  - Updated:   2015/02/09
# ----------------------------------------------------------------------------
# This is a from scratch clean version of a program I wrote years ago.
# I was tired of manually renaming and moving my anime downloads, so I wanted
# a script to do it for me.

from os.path import basename, dirname, isdir, join, exists
from os import listdir, walk, rmdir, unlink, rename as move_file
from fnmatch import filter as fnfilter
from glob import glob

# custom classes
from class_Config import Config, conf_exists

# ---------------------------------------------------------------------------
# functions
# ---------------------------------------------------------------------------
get_instring_list = lambda separator, string: [e.strip() for e in string.split(separator)]
get_instring_var = lambda operator, string: dict(zip(['name', 'value'], string.split(operator)))
get_instring_range = lambda separator, string: dict(zip(['start', 'end'], [int(i) for i in string.split(separator)]))

# ---------------------------------------------------------------------------
# classes
# ---------------------------------------------------------------------------
class AnimeConfig(Config):
	""" Contains all the preferences about how the episode files are going
		to be stored. """
	
	def get_shows(self):
		return [e for e in self if not e.endswith(':extra-goto')]
		
	def get_extra_goto_list(self, show):
		section = '%s:extra-goto' % show
		if not conf_exists(self[section]): return []
		return [dict(zip(['conditions', 'path'], get_instring_list('|', e))) for e in self.get_values_from_section(section)]
	
class EpisodesCollector:
	""" Iterates over directories to collect all the found episodes. """
	
	def __init__(self, paths, extensions):
		self.paths = paths
		self.extensions = extensions
		
	def get_files(self):
		list = []
		for path in self.paths:
			for extension in self.extensions:
				thisfiles = self.get_files_by_extension(path, extension)
				for file in thisfiles:
					list.append(file)
		return list
		
	def get_files_by_extension(self, path, extension):
		list = []
		for root, dirnames, filenames in walk(path):
			for filename in fnfilter(filenames, '*.%s' % extension):
				list.append(join(root, filename))
		return list

class EpisodeParser:
	""" * Gathers the config data for a matched show.
		* Generates the new filename for episode. """

	def __init__(self, file, anime_conf):
		self.file = file
		self.filename = basename(file)
		self.file_extension = self.filename.rsplit('.', 1)[1]
		self.set_filename_wellspaced()
		self.set_number()
		self.anime_conf = anime_conf
		self.id = self.goto = self.cfg_data = self.new_filename = None
		
	def matches_show(self):
		for e in self.anime_conf.get_shows():
			if e.lower() in self.filename_wellspaced.lower():
				self.id = e
				self.cfg_data = self.anime_conf[e]
				self.goto = self.cfg_data.goto
				return True
		return False
		
	def generate_new_filename(self):
		# allow only move when rename field is missing
		if not conf_exists(self.cfg_data.rename):
			self.new_filename = self.filename
			return
	
		# there's a number, it's episode or opening/ending
		if self.number != None:
		
			# automatic rename
			if self.cfg_data.rename == '-': source_rename = self.id
			else: source_rename = self.cfg_data.rename
		
			source_data = {
				'rename': source_rename,
				'number': self.add_zeros(self.number, self.cfg_data.digits),
				'number2d': self.add_zeros(self.number, 2)
			}
			
			# detect opening/ending
			for field in ['opening', 'ending']:
				if conf_exists(self.cfg_data[field]):
					value = dict(zip(['source', 'pattern'], get_instring_list('|', self.cfg_data[field])))
					if value['source'].lower() in self.filename_wellspaced.lower():
						self.new_filename = value['pattern'] % source_data
						break
			
			# pure episode, not opening/ending
			else:
				if conf_exists(self.cfg_data.pattern): pattern = self.cfg_data.pattern
				else: pattern = conf.common.default_pattern
				
				self.new_filename = pattern % source_data
			
		# there's not a number, should ask what to do (let me write a filename)
		else:
			self.new_filename = raw_input(u'[%s] new filename -> ' % self.filename)
			
		# add extension if needed
		if not self.new_filename.endswith('.%s' % self.file_extension):
			self.new_filename += '.%s' % self.file_extension
	
	def set_filename_wellspaced(self):
		different_spacer_strings = [self.filename.replace(spacer, ' ') for spacer in get_instring_list(',', conf.symbols.spacers)]
		self.filename_wellspaced = max(different_spacer_strings, key = lambda x: x.count(' '))
		
	def set_number(self):
		filename_only = self.filename_wellspaced.rsplit('.', 1)[0] # no extension
		for word in reversed(filename_only.split()):
			
			# consider versioned episode numbers, for example: 512v3
			version_parts = word.split('v')
			if len(version_parts) == 2: word = version_parts[0]
			
			try:
				number = int(word)
				if 0 <= number <= int(conf.common.max_sense_episode_number):
					self.number = number
					return
					
			except ValueError:
				pass
			
		self.number = None
		
	def add_zeros(self, number, digits):
		number_str = str(number)
		return ('0'*(int(digits)-len(number_str))) + number_str
	
class EpisodeDistributor:
	""" Sends a episode file to the wanted destiny. """
	
	def __init__(self, episode_parser):
		episode_parser.generate_new_filename()
		self.episode_parser = episode_parser
		
	def store(self):
		# read extra goto list and change goto value based on the set conditions
		for extra_goto in self.episode_parser.anime_conf.get_extra_goto_list(self.episode_parser.id):
			for condition in [c.strip() for c in extra_goto['conditions'].split('&&')]:
			
				var = get_instring_var('=', condition)
				if var['name'] == 'range':
					
					range = get_instring_range('-', var['value'])
					if range['start'] <= self.episode_parser.number <= range['end']:
						continue
					
				elif var['name'] == 'contains':
					
					if var['value'].lower() in self.episode_parser.filename_wellspaced.lower():
						continue
						
				break
				
			# line of conditions meet
			else:
				self.episode_parser.goto = extra_goto['path']
				break
		
		# try to move it
		try: move_file(self.episode_parser.file, join(self.episode_parser.goto, self.episode_parser.new_filename))
		except: return False
		
		return True
	
class DistributionReporter:
	
	def __init__(self):
		self.distributed = []
		
	def append(self, episode_distributor):
		self.distributed.append(episode_distributor)
		
	def get_count(self):
		return len(self.distributed)
		
	def get_done_files(self):
		return [e.episode_parser.file for e in self.distributed]
		
	def get_done_locations(self):
		done_files = self.get_done_files()
		return set([dirname(e) for e in done_files])
	
class Logger:
	
	def __init__(self):
		pass
		
	def save_line(self):
		pass
		
	def save_shortcut(self):
		pass
	
class TrashRemover:
	""" * Removes empty folders (recursive).
		* Removes torrent files (only on base directory). """

	def __init__(self, paths, done_locations):
		self.paths = paths
		self.done_locations = done_locations
		
	def clean_all(self):
		# remove empty folders and torrents
		for path in self.paths:
			if conf.cleanup.empty_folders == 'yes': self.remove_empty_folders(path, True)
			if conf.cleanup.base_torrents == 'yes': self.remove_base_torrents(path)
		
	def remove_empty_folders(self, path, not_this = False):
		if not isdir(path):
			return
	 
		# remove empty subfolders
		files = listdir(path)
		if len(files):
			for f in files:
				nextpath = join(path, f)
				if isdir(nextpath): self.remove_empty_folders(nextpath)
	 
		# if folder empty, delete it
		if not_this or path not in self.done_locations: return
		files = listdir(path)
		if len(files) == 0: rmdir(path)
			
	def remove_base_torrents(self, path):
		torrents = glob(join(path, '*.torrent'))
		for file in torrents:
			try: unlink(file)
			except: pass
	
class FinalMenu:
	
	def __init__(self, distribution_reporter):
		self.distribution_reporter = distribution_reporter
		
	def interact(self):
		pass

# ---------------------------------------------------------------------------
# program
# ---------------------------------------------------------------------------
if __name__ == '__main__':
	
	# retrieve config values
	conf = Config('conf.ini')
	anime_conf = AnimeConfig(conf.paths.sources)
	
	# collect the episode files
	source_folders = conf.get_values_from_section('source-folders')
	episodes_collector = EpisodesCollector(source_folders, get_instring_list(',', conf.common.extensions))
	files = episodes_collector.get_files()
	
	# iterate over found files and get episode parsers
	episode_parsers = []
	for file in files:
	
		episode_parser = EpisodeParser(file, anime_conf)
		if not episode_parser.matches_show():
			continue
			
		episode_parsers.append(episode_parser)
		
	# group episodes by anime name
	episode_groups = {}
	for episode_parser in episode_parsers:
	
		if not episode_groups.has_key(episode_parser.id):
			episode_groups[episode_parser.id] = []
		
		episode_groups[episode_parser.id].append(episode_parser)
	
	# iterate over groups to distribute episodes
	print 'Processing episodes...\n'
	global_distribution_reporter = DistributionReporter()
	for id in sorted(episode_groups.keys()):
		
		print ' >> %s' % id,
		if len(episode_groups[id]) > int(conf.common.max_process_dots):
			print conf.symbols.dot * 3,
			dots = False
		else: dots = True
		
		local_distribution_reporter = DistributionReporter()
		for episode_parser in episode_groups[id]:
		
			episode_distributor = EpisodeDistributor(episode_parser)
			if not episode_distributor.store():
				print conf.symbols.error,
				continue
			
			if dots: print conf.symbols.dot,
			local_distribution_reporter.append(episode_distributor)
			global_distribution_reporter.append(episode_distributor)
			
			logger = Logger()
			logger.save_line()
			logger.save_shortcut()
			
		print 'x%i' % local_distribution_reporter.get_count()
		
	# clean trash
	trash_remover = TrashRemover(source_folders, global_distribution_reporter.get_done_locations())
	trash_remover.clean_all()
	
	# show final menu
	final_menu = FinalMenu(global_distribution_reporter)
	final_menu.interact()
	