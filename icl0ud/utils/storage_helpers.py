from twisted.protocols.basic import FileSender


class FileRangeSender(FileSender):
	# TODO handle closed client connection; reproduce by disabling/enabling
	# PhotoStream on iOS, then disable during GET
	def beginFileTransfer(self, file, consumer, rangeBegin, rangeEnd, transform = None):
		if not rangeBegin < rangeEnd:
			raise ValueError('rangeBegin >= rangeEnd')
		self.rangeBegin = rangeBegin
		self.rangeEnd = rangeEnd
		if file:
			file.seek(rangeBegin)
		return FileSender.beginFileTransfer(self, file, consumer, transform)

	def resumeProducing(self):
		# print 'resume'
		chunk = ''
		if self.file:
			# ensure rangeBegin < rangeEnd, see above
			bytesToRead = self.rangeEnd - self.file.tell()
			bytesToRead = min(bytesToRead, self.CHUNK_SIZE)

			if bytesToRead > 0:
				chunk = self.file.read(bytesToRead)
		if not chunk:
			self.file = None
			self.consumer.unregisterProducer()
			if self.deferred:
			    self.deferred.callback(self.lastSent)
			    self.deferred = None
			return

		if self.transform:
			  chunk = self.transform(chunk)
		self.consumer.write(chunk)
		self.lastSent = chunk[-1]
