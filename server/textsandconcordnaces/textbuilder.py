def buildfulltext(work, levelcount, higherlevels, linesevery, cursor):
	"""
	make a readable/printable version of a work and send it to its own page
	huge works will overwhelm the ability of most/all browsers to parse that much html
	printing to pdf is a good idea, but for the incredibly slow pace of such
	:param work:
	:param levelcount:
	:param higherlevels:
	:param linesevery:
	:param cursor:
	:return:
	"""
	query = 'SELECT * FROM ' + work + ' ORDER BY index ASC'
	cursor.execute(query)
	results = cursor.fetchall()
	
	# will mark/reset every time you get to a major level shift
	output = []
	memory = []
	for m in range(0, len(higherlevels)):
		memory.append(0)
	linecount = 0
	for line in results:
		linecount += 1
		linecore = line[7]
		currlevels = []
		for c in range(5, 5 - len(higherlevels), -1):
			currlevels.append(line[c])
		if currlevels != memory:
			linecount = linesevery
			memory = currlevels
		if linecount % linesevery == 0:
			linehtml = linecore + '&nbsp;&nbsp;<span class="browsercite">('
			for level in range(7 - levelcount, 7):
				linehtml += str(line[level]) + '.'
			linehtml = linehtml[:-1] + ')</span>'
		else:
			linehtml = linecore
		output.append(linehtml)

	return output
