
def httpError(request, code, message):
	request.setResponseCode(code)
	return '%i %s\n' % (code, message)

def http403(request):
	return httpError(request, 403, 'Forbidden')

def http404(request):
	return httpError(request, 404, 'Not Found')
