#DATE=$(shell date +%Y-%m-%d)
#YEAR=$(shell date +%Y)
#DIR=webola-$(DATE)
#REVNO=$(shell bzr revno)
VERSION=$(shell date +%Y.%-m.%-d)

push:
#	git remote set-url origin https://svoigtmann:$(TOKEN)@github.com/svoigtmann/webola.git
# add ssh-key to gitlab account (avatar -> edit profile) and run 'ssh -T git@github.com'
	./webola/prepare_version.py
#	git push origin

install:
	./webola/prepare_version.py
	sudo pip uninstall webola
	python -m build
	sudo -H pip install dist/webola-$(VERSION)-py3-none-any.whl

dot: webola/database.png

%.dot: %.py
	../db2dot/db2dot.py -c $< > $@

%.png: %.dot
	dot -Tpng $< > $@

# requires pyqt5-dev-tools
icons.py: resources/resources.qrc resources/icons.tex
	cd resources && make
	cp resources/icons.py .

Startliste\ 6.\ Bogenlauf\ 2019.txt: Startliste\ 6.\ Bogenlauf\ 2019.pdf
	pdftotext -nopgbrk -layout "$<" 

webola.png:
	pydeps webola.py -T png --noshow -xx webola.database webola.utils webola.buttons webola.containers webola.dialogs --max-bacon 5
#	pydeps webola.py -T png --noshow -xx webola.database

requirements.txt: 
	@pipreqs --force
	@sed -i 's/==.*//'      requirements.txt # skip package versions
	@sed -i '/setuptools/d' requirements.txt # setuptools only needed for packaging
	@cat requirements.txt

dist:
	pyinstaller --onefile --hidden-import pony.orm.dbproviders.sqlite webola.py

#zip: requirements.txt
#	rm -f $(DIR).zip
#	mkdir -p $(DIR)/webola
#	cp webola/*.py $(DIR)/webola/
#	cp webola.py startliste_dummy.xlsx $(DIR)/
#	cat README | sed "s/__VERSION_TAG__/$(REVNO) ($(DATE))/" | sed "s/__YEAR__/$(YEAR)/"> $(DIR)/README
#	zip -r $(DIR) $(DIR)
#	rm -rf $(DIR)

clean:
	rm -rf build dist tex-tmp
	find . -iname __pycache__ | xargs -i rm -rf {}
	find . -iname "*.pyc" | xargs -i rm {}
	find . -iname "*~" | xargs -i rm {}
	bash -c "rm -f backup-*.{tex,pdf,xlsx,html} ziel.{html,tex,pdf,xlsx}"
	cd resources && rm -f icons.pdf minus.png plus.png webola.png run.png result.png battery_critical.png battery_critical_powered.png battery_low.png battery_low_powered.png battery_medium.png battery_medium_powered.png battery_full.png battery_full_powered.png target.png name_team.png team_name.png fullscreen.png

#dump:
#	echo '.dump' | sqlite3 <file>.sql > test.dump
#  	edit test.dump as needed and remove <file>.sql
#	cat test.dump | sqlite3 <file>.sql

.PHONY: zip requirements.txt webola.png
