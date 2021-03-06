CBS_LIST = 'http://www.cbs.com/video/'

API_URL = "http://api.cnet.com/restApi/v1.0/videoSearch?categoryIds=%s&orderBy=productionDate~desc,createDate~desc&limit=20&iod=images,videoMedia,relatedLink,breadcrumb,relatedAssets,broadcast,lowcache&partTag=cntv&showBroadcast=true"
API_NAMESPACE  = {'l':'http://api.cnet.com/rest/v1.0/ns'}

SHOWNAME_LIST = 'http://cbs.feeds.theplatform.com/ps/JSON/PortalService/1.6/getReleaseList?PID=GIIJWbEj_zj6weINzALPyoHte4KLYNmp&startIndex=1&endIndex=50&query=contentCustomBoolean|EpisodeFlag|%s&query=CustomBoolean|IsLowFLVRelease|false&query=contentCustomText|SeriesTitle|%s&query=servers|%s&sortField=airdate&sortDescending=true&field=airdate&field=author&field=description&field=length&field=PID&field=thumbnailURL&field=title&field=encodingProfile&contentCustomField=label'
CBS_SMIL = 'http://release.theplatform.com/content.select?format=SMIL&Tracking=true&balance=true&pid=%s'
SERVERS = [
	'CBS%20Production%20Delivery%20h264%20Akamai',
	'CBS%20Production%20News%20Delivery%20Akamai%20Flash',
	'CBS%20Production%20Entertainment%20Delivery%20Akamai%20Flash',
	'CBS%20Production%20Entertainment%20Delivery%20Akamai%20Flash%20Progressive',
	'CBS%20Delivery%20Akamai%20Flash'
]
CATEGORIES = [
	{"title": "Primetime",	"label": "primetime"},
	{"title": "Daytime",	"label": "daytime"},
	{"title": "Late Night",	"label": "latenight"},
	{"title": "Classics",	"label": "classics"}
]

CAROUSEL_URL = 'http://www.cbs.com/carousels/%s/video/%s/%s/0/100/'

API_TITLES = ["48 Hours Mystery"]
API_IDS = {"48 Hours Mystery": {"episodes":"503443", "clips":"18559"}}

RE_FULL_EPS = Regex("\.loadUpCarousel\('Full Episodes','([0-9]_video_.+?)', '(.+?)', ([0-9]+), .+?\);", Regex.DOTALL|Regex.IGNORECASE)
RE_CLIPS = Regex("loadUpCarousel\('Newest Clips','([0-9]_video_.+?)', '(.+?)', ([0-9]+), .+?\);", Regex.DOTALL|Regex.IGNORECASE)

####################################################################################################
def Start():

	ObjectContainer.title1 = 'CBS'
	HTTP.CacheTime = CACHE_1HOUR
	HTTP.Headers['User-Agent'] = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.8; rv:18.0) Gecko/20100101 Firefox/18.0'

####################################################################################################
@handler('/video/cbs', 'CBS')
def MainMenu():

	oc = ObjectContainer()

	for category in CATEGORIES:
		oc.add(DirectoryObject(
			key = Callback(Shows, title=category['title'], category=category['label']),
			title = category['title']
		))

	return oc

####################################################################################################
@route('/video/cbs/shows')
def Shows(title, category):

	oc = ObjectContainer(title2=title)

	for item in HTML.ElementFromURL(CBS_LIST).xpath('//div[@id="' + category + '"]//div[@id="show_block_interior"]'):
		title = item.xpath('.//img')[0].get('alt')
		display_title = title
		url = item.xpath('.//a')[0].get('href')

		if 'http://www.cbs.com/' not in url:
			url = 'http://www.cbs.com' + url

		thumb = item.xpath('.//img')[0].get('src')
		if 'http://www.cbs.com/' not in thumb:
			thumb = 'http://www.cbs.com' + thumb

		### Naming differences
		if title == 'Late Show With David Letterman':
			title = 'Late Show'

		if title == 'The Late Late Show with Craig Ferguson':
			title = 'The Late Late Show'

		if title == 'Star Trek: The Original Series':
			title = 'Star Trek Remastered'
			display_title += ' (HD only)' ### THESE ARE HD FEEDS - NEED TO FIND LOWER QUALITY

		if title == '48 Hours Mystery':
			title = '48 Hours'

		if title == 'CSI: Crime Scene Investigation':
			title = 'CSI:'

		if 'SURVIVOR' in title:
			title = 'Survivor'

		if title == 'The Bold And The Beautiful':
			title = 'Bold and the Beautiful'

		if title == 'The Young And The Restless':
			title = 'Young and the Restless'

		if title in ['Live on Letterman']:
			continue ### THESE ARE NOT ACTUAL SHOWS AND ARE EXCLUDED

		if 'GRAMMY' in title:
			title = 'Grammys'

		title = title.replace(' ', '%20').replace('&', '%26').replace("'", '')

		oc.add(DirectoryObject(
			key = Callback(EpisodesAndClips, title=title, display_title=display_title, url=url),
			title = display_title,
			thumb = thumb
		))

	return oc

####################################################################################################
@route('/video/cbs/epsandclips')
def EpisodesAndClips(title, display_title, url):

	oc = ObjectContainer(title2=display_title)

	if display_title not in API_TITLES:
		oc.add(DirectoryObject(key=Callback(Videos, full_episodes='true', title=title, display_title=display_title, url=url), title='Full Episodes'))
		oc.add(DirectoryObject(key=Callback(Videos, full_episodes='false', title=title, display_title=display_title, url=url), title='Clips'))
	else:
		oc.add(DirectoryObject(key=Callback(APIVideos, full_episodes='true', title=title, display_title=display_title, url=url), title='Full Episodes'))
		oc.add(DirectoryObject(key=Callback(APIVideos, full_episodes='false', title=title, display_title=display_title, url=url), title='Clips'))

	return oc

####################################################################################################
@route('/video/cbs/videos')
def Videos(full_episodes, title, display_title, url):

	oc = ObjectContainer(title2=display_title)

	if url.endswith('/video/'):
		pass
	else:
		url = '%s/video/' % url.rstrip('/')

	try:
		page = HTTP.Request(url).content
	except:
		return ObjectContainer(header="CBS", message="An error has occurred. No content found.")

	if full_episodes == 'true':
		episodes = []
		request_params = RE_FULL_EPS.findall(page)

		if request_params != None:
			for i in range(len(request_params)):
				show_id = request_params[i][2]
				server = request_params[i][0]
				hash = request_params[i][1]
				episode_list = JSON.ObjectFromURL(CAROUSEL_URL % (show_id, server, hash))

				for episode in episode_list['itemList']:
					video_title = episode['title']
					date = Datetime.FromTimestamp(int(episode['airDate'])/1000).date()
					summary = episode['description']
					video_url = episode['url']

					try:
						index = int(episode['episodeNum'])
						season = int(episode['seasonNum'])
					except:
						index = None
						season = None

					show = episode['seriesTitle']
					duration = int(episode['duration'])*1000
					content_rating = episode['rating']
					thumbs = SortImages(episode['thumbnailSet'])
					episode_string = "S%sE%s - %s" % (season, index, video_title)

					if episode_string not in episodes:
						oc.add(EpisodeObject(
							url = video_url,
							title = video_title,
							show = show,
							index = index,
							season = season,
							summary = summary,
							duration = duration,
							originally_available_at = date,
							content_rating = content_rating,
							thumb = Resource.ContentsOfURLWithFallback(url=thumbs)
						))

						episodes.append(episode_string)
					else:
						pass
                else:
			pass

		if len(oc) < 1:
			return OlderVideos(full_episodes=full_episodes, title=title, display_title=display_title, url=url)
		else:
			oc.add(DirectoryObject(
				key = Callback(OlderVideos, full_episodes=full_episodes, title=title, display_title=display_title, url=url),
				title = "Older Episodes"
			))
	else:
		request_params = RE_CLIPS.findall(page)

		if request_params != None:
			for i in range(len(request_params)):
				show_id = request_params[i][2]
				server = request_params[i][0]
				hash = request_params[i][1]
				clip_list = JSON.ObjectFromURL(CAROUSEL_URL % (show_id, server, hash))

				for clip in clip_list['itemList']:
					video_title = clip['title']
					summary = clip['description']

					if video_title == '':
						video_title = summary

					date = Datetime.FromTimestamp(int(clip['pubDate'])/1000).date()
					video_url = clip['url']
					duration = int(clip['duration'])*1000
					thumbs = SortImages(clip['thumbnailSet'])

					oc.add(VideoClipObject(
						url = video_url,
						title = video_title,
						summary = summary,
						duration = duration,
						originally_available_at = date,
						thumb = Resource.ContentsOfURLWithFallback(url=thumbs)
					))

					if len(oc) > 24:
						break

				if len(oc) > 24:
						break
		else:
			pass

		if len(oc) < 1:
			return OlderVideos(full_episodes=full_episodes, title=title, display_title=display_title, url=url)
		else:
			oc.add(DirectoryObject(
				key = Callback(OlderVideos, full_episodes=full_episodes, title=title, display_title=display_title, url=url),
				title = "Older clips"
			))

	return oc

####################################################################################################
@route('/video/cbs/oldervideos')
def OlderVideos(full_episodes, title, display_title, url):

	oc = ObjectContainer(title2=display_title)
	show_title = title
	processed_titles = []

	for server in SERVERS:
		feed_url = SHOWNAME_LIST % (full_episodes, show_title, server)
		Log(' --> Checking server: ' + server)
		Log(' --> URL: ' + url)

		try:
			feeds = JSON.ObjectFromURL(feed_url)
			encoding = ''

			for item in feeds['items']:
				title = item['contentCustomData'][0]['value']

				if title not in processed_titles:
					if "HD" in item['encodingProfile']:
						encoding = " - HD " + item['encodingProfile'][3:8].replace(' ', '')
					else:
						encoding = ''

					video_title = title + str(encoding)
					pid = item['PID']
					video_url = url + '?play=true&pid=' + pid
					summary = item['description'].replace('In Full:', '')
					duration = item['length']
					thumb = item['thumbnailURL']
					airdate = int(item['airdate'])/1000
					originally_available_at = Datetime.FromTimestamp(airdate).date()

					if full_episodes == "true":
						oc.add(EpisodeObject(
							url = video_url,
							show = display_title,
							title = video_title,
							summary = summary,
							duration = duration,
							originally_available_at = originally_available_at,
							thumb = Resource.ContentsOfURLWithFallback(url=thumb)
						))
					else:
						if video_title == '':
							video_title = summary

						oc.add(VideoClipObject(
							url = video_url,
							title = video_title,
							summary = summary,
							duration = duration,
							originally_available_at = originally_available_at,
							thumb = Resource.ContentsOfURLWithFallback(url=thumb)
						))

					processed_titles.append(title)

					if len(oc) > 49:
						break

				if len(oc) > 49:
					break
			Log(' --> Success! Found ' + str(len(feeds['items'])) + ' items')
			if len(oc) > 49:
				break
		except:
			Log(' --> Failed!')
			pass

		if len(oc) > 49:
			break

	if len(oc) < 1:
		return ObjectContainer(header='Empty', message="There aren't any items")
	else:
		return oc

####################################################################################################
@route('/video/cbs/apivideos')
def APIVideos(full_episodes, title, display_title, url):

	oc = ObjectContainer(title2=display_title)

	if full_episodes == 'true':
		data = XML.ElementFromURL(API_URL % API_IDS[display_title]['episodes'])

		for episode in data.xpath('//l:Video', namespaces=API_NAMESPACE):
			video_url = episode.xpath('.//l:CBSURL', namespaces=API_NAMESPACE)[0].text
			title = episode.xpath('.//l:Title', namespaces=API_NAMESPACE)[0].text
			summary = episode.xpath('.//l:Description', namespaces=API_NAMESPACE)[0].text
			date = Datetime.ParseDate(episode.xpath('.//l:ProductionDate', namespaces=API_NAMESPACE)[0].text).date()
			duration = int(episode.xpath('.//l:LengthSecs', namespaces=API_NAMESPACE)[0].text)*1000
			images = episode.xpath('.//l:Images/l:Image', namespaces=API_NAMESPACE)
			thumbs = SortImagesFromAPI(images)
			show = display_title
			rating = episode.xpath('.//l:ContentRatingOverall', namespaces=API_NAMESPACE)[0].text

			try: season = int(episode.xpath('.//l:SeasonNumber', namespaces=API_NAMESPACE)[0].text)
			except: season = None

			try: index = int(episode.xpath('.//l:EpisodeNumber', namespaces=API_NAMESPACE)[0].text)
			except: index = None

			if show and season and index:
				oc.add(EpisodeObject(
					url = video_url,
					title = title,
					show = show,
					summary = summary,
					originally_available_at = date,
					duration = duration,
					content_rating = rating,
					season = season,
					index = index,
					thumb = Resource.ContentsOfURLWithFallback(url=thumbs)
				))
			else:
				oc.add(VideoClipObject(
					url = video_url,
					title = title,
					summary = summary,
					originally_available_at = date,
					duration = duration,
					content_rating = rating,
					thumb = Resource.ContentsOfURLWithFallback(url=thumbs)
				))
	else:
		data = XML.ElementFromURL(API_URL % API_IDS[display_title]['clips'])

		for clip in data.xpath('//l:Video', namespaces=API_NAMESPACE):
			video_url = clip.xpath('.//l:CBSURL', namespaces=API_NAMESPACE)[0].text
			title = clip.xpath('.//l:Title', namespaces=API_NAMESPACE)[0].text
			summary = clip.xpath('.//l:Description', namespaces=API_NAMESPACE)[0].text

			if title == '':
				title = summary

			date = Datetime.ParseDate(clip.xpath('.//l:ProductionDate', namespaces=API_NAMESPACE)[0].text).date()
			duration = int(clip.xpath('.//l:LengthSecs', namespaces=API_NAMESPACE)[0].text)*1000
			images = clip.xpath('.//l:Images/l:Image', namespaces=API_NAMESPACE)
			thumbs = SortImagesFromAPI(images)

			oc.add(VideoClipObject(
				url = video_url,
				title = title,
				originally_available_at = date,
				duration = duration,
				summary = summary,
				thumb = Resource.ContentsOfURLWithFallback(url=thumbs)
			))

	return oc

####################################################################################################
@route('/video/cbs/sortimages')
def SortImages(images=[]):

	sorted_thumbs = sorted(images, key=lambda thumb : int(thumb['height']), reverse=True)
	thumb_list = []

	for thumb in sorted_thumbs:
		thumb_list.append(thumb['url'])

		if len(thumb_list) > 2:
			break

	return thumb_list

####################################################################################################
@route('/video/cbs/sortapiimages')
def SortImagesFromAPI(images=[]):

	thumbs = []

	for image in images:
		height = image.get('height')
		url = image.xpath('./l:ImageURL', namespaces=API_NAMESPACE)[0].text
		thumbs.append({'height':height, 'url':url})

	sorted_thumbs = sorted(thumbs, key=lambda thumb: int(thumb['height']), reverse=True)
	thumb_list = []

	for thumb in sorted_thumbs:
		thumb_list.append(thumb['url'])

		if len(thumb_list) > 2:
			break

	return thumb_list
