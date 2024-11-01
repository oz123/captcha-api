OPTS = 

build:
	docker build -t captcha-api .
run:
	docker run --rm -v $(CURDIR):/tmp/ --name captcha -p 5000:5000 -e SQLALCHEMY_DATABASE_URI=sqlite:///tmp/captcha.db -e CAPTCHA_API_CONFIG=captcha.cfg captcha-api $(OPTS)
