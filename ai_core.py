import random
import datetime
import numpy
import os
import pickle
from pybrain3.datasets import SupervisedDataSet, UnsupervisedDataSet
from pybrain3.structure import LinearLayer
from pybrain3.supervised.trainers import BackpropTrainer
from pybrain3.tools.shortcuts import buildNetwork
from events.models import Event


class Tools:
	# region Constants
	# Weekdays
	MON = 2  # 0b1000000
	TUE = 3  # 0b0100000
	WED = 4  # 0b0010000
	THU = 5  # 0b0001000
	FRI = 6  # 0b0000100
	SAT = 7  # 0b0000010
	SUN = 1  # 0b0000001

	# Map of categories with ids
	cat_map = [
		{'name': 'default', 'id': 0, 'time': 8, 'day': SUN},  # any not found category
		{'name': 'trip', 'id': 1, 'time': 9, 'day': FRI},  # ex: school trips
		{'name': 'hang out', 'id': 2, 'time': 19, 'day': SAT},  # ex: club, friends
		{'name': 'sport', 'id': 3, 'time': 20, 'day': WED},  # ex: workout, jogging
		{'name': 'game', 'id': 4, 'time': 21, 'day': SUN},  # ex: computer games, pool
		{'name': 'project', 'id': 5, 'time': 14, 'day': MON},  # ex: one time project works
		{'name': 'meet', 'id': 6, 'time': 12, 'day': MON},  # ex: off work meetings
		{'name': 'party', 'id': 7, 'time': 15, 'day': SUN},  # ex: any type of party
		{'name': 'study', 'id': 8, 'time': 19, 'day': TUE},  # ex: do homeworks
		{'name': 'shop', 'id': 9, 'time': 13, 'day': THU},  # ex: buy clothes
	]

	# endregion

	@staticmethod
	def objdump(dmp_obj, dmp_filename):
		dump = open(dmp_filename, 'wb')
		pickle.dump(dmp_obj, dump)
		dump.close()

	@staticmethod
	def objrecv(dmp_filename):
		dump = open(dmp_filename, 'rb')
		dmp_obj = pickle.load(dump)
		dump.close()
		return dmp_obj

	@staticmethod
	def time_add(_time, _add):
		time = datetime.datetime(
			year=int(_time / 1000000),
			month=int(_time / 10000) % 100,
			day=int(_time / 100) % 100,
			hour=int(_time % 100)
		)

		if _add >= 0:
			time += datetime.timedelta(hours=int(_add / 60))
		else:
			time -= datetime.timedelta(hours=int(-_add / 60))
		return int("%02d%02d%02d%02d" % (time.year % 100, time.month, time.day, time.hour))


class CategoryAdvisor:
	# region Notes on using this class
	# In order to use dataset, history must contain >2*OBSERVE_LENGTH (which is >20)
	# endregion

	# region Constants
	PROJECT_DIR = 'myweek-ai-data'
	KEY_TIME = 'time'
	KEY_DAY = 'day'

	NET_EXT = 'netdmp'
	DST_EXT = 'dstdmp'

	OBSERVE_LENGTH = 5
	PREDICT_LENGTH = 1
	# endregion

	# region Variables
	bprnetw_hr = None  # network for hour
	bprnetw_dy = None  # network for weekday
	dataset_hr = None  # dataset for hour
	dataset_dy = None  # dataset for hour
	user = None
	category_id = None

	# endregion

	@staticmethod
	def create(user, category_id, network_hr=None, dataset_hr=None, network_dy=None, dataset_dy=None):
		res = CategoryAdvisor()

		res.user = user
		res.category_id = category_id

		if network_hr is None:
			res.bprnetw_hr = buildNetwork(CategoryAdvisor.OBSERVE_LENGTH, 20, CategoryAdvisor.PREDICT_LENGTH, outclass=LinearLayer, bias=True, recurrent=True)
		else:
			res.bprnetw_hr = network_hr

		if dataset_hr is None:
			res.dataset_hr = SupervisedDataSet(CategoryAdvisor.OBSERVE_LENGTH, CategoryAdvisor.PREDICT_LENGTH)
		else:
			res.dataset_hr = dataset_hr

		if network_dy is None:
			res.bprnetw_dy = buildNetwork(CategoryAdvisor.OBSERVE_LENGTH, 20, CategoryAdvisor.PREDICT_LENGTH, outclass=LinearLayer, bias=True, recurrent=True)
		else:
			res.bprnetw_dy = network_dy

		if dataset_dy is None:
			res.dataset_dy = SupervisedDataSet(CategoryAdvisor.OBSERVE_LENGTH, CategoryAdvisor.PREDICT_LENGTH)
		else:
			res.dataset_dy = dataset_dy

		return res

	@staticmethod
	def recover(user, category_id):
		if not CategoryAdvisor.is_backed_up(user, category_id):
			return False

		res = CategoryAdvisor()

		res.user = user
		res.category_id = category_id
		res.bprnetw_hr = Tools.objrecv('~/%s/%s-%d-hr.%s' % (res.PROJECT_DIR, user.username, category_id, res.NET_EXT))
		res.dataset_hr = Tools.objrecv('~/%s/%s-%d-hr.%s' % (res.PROJECT_DIR, user.username, category_id, res.DST_EXT))
		res.bprnetw_dy = Tools.objrecv('~/%s/%s-%d-dy.%s' % (res.PROJECT_DIR, user.username, category_id, res.NET_EXT))
		res.dataset_dy = Tools.objrecv('~/%s/%s-%d-dy.%s' % (res.PROJECT_DIR, user.username, category_id, res.DST_EXT))

		return res

	@staticmethod
	def is_backed_up(user, category_id):
		return \
			os.path.exists('~/%s' % CategoryAdvisor.PROJECT_DIR) and \
			os.path.isfile('~/%s/%s-%d-hr.%s' % (CategoryAdvisor.PROJECT_DIR, user.username, category_id, CategoryAdvisor.NET_EXT)) and \
			os.path.isfile('~/%s/%s-%d-hr.%s' % (CategoryAdvisor.PROJECT_DIR, user.username, category_id, CategoryAdvisor.DST_EXT)) and \
			os.path.isfile('~/%s/%s-%d-dy.%s' % (CategoryAdvisor.PROJECT_DIR, user.username, category_id, CategoryAdvisor.NET_EXT)) and \
			os.path.isfile('~/%s/%s-%d-dy.%s' % (CategoryAdvisor.PROJECT_DIR, user.username, category_id, CategoryAdvisor.DST_EXT))

	def backup(self):
		# create backup files in home directory
		if not os.path.exists('~/%s' % self.PROJECT_DIR):
			os.makedirs('~/%s' % self.PROJECT_DIR)

		Tools.objdump(dmp_obj=self.bprnetw_hr, dmp_filename='~/%s/%s-%d-hr.%s' % (self.PROJECT_DIR, self.user, self.category_id, self.NET_EXT))
		Tools.objdump(dmp_obj=self.dataset_hr, dmp_filename='~/%s/%s-%d-hr.%s' % (self.PROJECT_DIR, self.user, self.category_id, self.DST_EXT))
		Tools.objdump(dmp_obj=self.bprnetw_dy, dmp_filename='~/%s/%s-%d-dy.%s' % (self.PROJECT_DIR, self.user, self.category_id, self.NET_EXT))
		Tools.objdump(dmp_obj=self.dataset_dy, dmp_filename='~/%s/%s-%d-dy.%s' % (self.PROJECT_DIR, self.user, self.category_id, self.DST_EXT))

	def retrain_complete(self, cmp_history_hr, cmp_history_dy):
		res = False

		if len(cmp_history_hr) >= CategoryAdvisor.OBSERVE_LENGTH:
			self.dataset_hr.clear()

			data_length = len(cmp_history_hr)

			for n in range(data_length):
				if n + (CategoryAdvisor.OBSERVE_LENGTH - 1) + CategoryAdvisor.PREDICT_LENGTH < data_length:
					self.dataset_hr.addSample(cmp_history_hr[n:n + CategoryAdvisor.OBSERVE_LENGTH], cmp_history_hr[n + 1:n + 1 + CategoryAdvisor.PREDICT_LENGTH])

			trainer = BackpropTrainer(self.bprnetw_hr, self.dataset_hr)
			trainer.trainEpochs(100)

			res = True

		if len(cmp_history_dy) >= CategoryAdvisor.OBSERVE_LENGTH:
			self.dataset_dy.clear()

			data_length = len(cmp_history_dy)

			for n in range(data_length):
				if n + (CategoryAdvisor.OBSERVE_LENGTH - 1) + CategoryAdvisor.PREDICT_LENGTH < data_length:
					self.dataset_dy.addSample(cmp_history_dy[n:n + CategoryAdvisor.OBSERVE_LENGTH], cmp_history_dy[n + 1:n + 1 + CategoryAdvisor.PREDICT_LENGTH])

			trainer = BackpropTrainer(self.bprnetw_dy, self.dataset_dy)
			trainer.trainEpochs(100)

			return res
		else:
			return False

	def retrain_single(self, value_hr, value_dy):
		# train the hour advisor network
		inp = numpy.append(self.dataset_hr['input'][-1][1:], self.dataset_hr['target'][-1])
		self.dataset_hr.addSample(inp, [value_hr])

		trainer_hr = BackpropTrainer(self.bprnetw_hr, self.dataset_hr)
		trainer_hr.trainEpochs(100)

		# train the day advisor network
		inp = numpy.append(self.dataset_dy['input'][-1][1:], self.dataset_dy['target'][-1])
		self.dataset_dy.addSample(inp, [value_dy])

		trainer_dy = BackpropTrainer(self.bprnetw_dy, self.dataset_dy)
		trainer_dy.trainEpochs(100)

	def suggest(self):
		# calculate time
		ts = UnsupervisedDataSet(CategoryAdvisor.OBSERVE_LENGTH, )
		ts.addSample(self.dataset_hr['input'][-1])
		time = int(self.bprnetw_hr.activateOnDataset(ts)[0][0])

		# calculate day
		ts.clear()
		ts.addSample(self.dataset_hr['input'][-1])
		day = int(self.bprnetw_dy.activateOnDataset(ts)[0][0])

		return {self.KEY_TIME: time, self.KEY_DAY: day}

	def suggest_int(self):
		value = self.suggest()

		if value[CategoryAdvisor.KEY_DAY] < 1:
			value[CategoryAdvisor.KEY_DAY] = 1
		if value[CategoryAdvisor.KEY_DAY] > 7:
			value[CategoryAdvisor.KEY_DAY] = 7

		if value[CategoryAdvisor.KEY_TIME] < 0:
			value[CategoryAdvisor.KEY_TIME] = 0
		if value[CategoryAdvisor.KEY_TIME] > 23:
			value[CategoryAdvisor.KEY_TIME] = 23

		return value[CategoryAdvisor.KEY_TIME] * 10 + value[CategoryAdvisor.KEY_DAY]


# region Variables
# 2D map. Classification: rows=users, columns=category_ids
advisors = {}

# endregion

# region Check & Update support
date_today = -1


def check_retrain(user):
	global date_today
	temp_date = datetime.datetime.now().day

	if temp_date > date_today:
		init_advisors(user=user)
		date_today = temp_date


# endregion


def init_advisors(user):
	if user not in advisors:
		temp = {}
		for category in Tools.cat_map:
			category_id = category['id']

			# create or load the advisor object from storage
			temp[category_id] = CategoryAdvisor.recover(user=user, category_id=category_id) if CategoryAdvisor.is_backed_up(user=user, category_id=category_id) else CategoryAdvisor.create(
				user=user, category_id=category_id)

			# populate data if not exists or lacks
			if not Event.objects.filter(user=user, category_id=category_id).exists() or len(Event.objects.filter(user=user, category_id=category_id)) < 10:
				day = category['day']
				start_time = category['time']
				for x in range(0, 10):
					Event.objects.create_event(user=user, day=day, start_time=start_time + random.randrange(-1, 2, 1), length=60, category_id=category['id'], is_active=False)

			# retrain the network completely
			data_hr = []
			data_dy = []
			for event in Event.objects.filter(user=user, category_id=category_id):
				data_hr.append(event.start_time)
				data_dy.append(event.day)

			temp[category_id].retrain_complete(data_hr, data_dy)
		# add the created bunch of advisors
		advisors[user] = temp


def request_suggestion(user, category_id):
	found = False
	for _ctg in Tools.cat_map:
		if _ctg['id'] == category_id:
			found = True
			break
	if found is False:
		category_id = Tools.cat_map[0]['id']  # use default category if not found
	advisor = advisors[user][category_id]
	return advisor.suggest_int()
