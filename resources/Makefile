PICS=minus.png plus.png webola.png run.png result.png target.png name_team.png team_name.png fullscreen.png

all: icons.py

icons.pdf: icons.tex
	mkdir -p tex-tmp
	pdflatex -interaction=batchmode -output-directory=tex-tmp $<
	cp tex-tmp/$@ .

minus.png: icons.pdf
	convert icons.pdf[0] -size 480x480 -transparent white -blur 1x1 $@

plus.png: icons.pdf
	convert icons.pdf[1] -size 480x480 -transparent white -blur 1x1 $@

webola.png: icons.pdf
	convert icons.pdf[2] -size 480x480 -transparent white -blur 1x1 $@

run.png: icons.pdf
	convert icons.pdf[3] -size 480x480 -transparent white -blur 1x1 $@

result.png: icons.pdf
	convert icons.pdf[4] -size 480x480 -transparent white -blur 1x1 $@

battery:
	convert icons.pdf[5]  -size 480x480 -transparent white -blur 1x1 battery_critical.png
	convert icons.pdf[6]  -size 480x480 -transparent white -blur 1x1 battery_critical_powered.png
	convert icons.pdf[7]  -size 480x480 -transparent white -blur 1x1 battery_low.png
	convert icons.pdf[8]  -size 480x480 -transparent white -blur 1x1 battery_low_powered.png
	convert icons.pdf[9] -size 480x480 -transparent white -blur 1x1 battery_medium.png
	convert icons.pdf[10] -size 480x480 -transparent white -blur 1x1 battery_medium_powered.png
	convert icons.pdf[11] -size 480x480 -transparent white -blur 1x1 battery_full.png
	convert icons.pdf[12] -size 480x480 -transparent white -blur 1x1 battery_full_powered.png

target.png: icons.pdf
	convert icons.pdf[13] -size 480x480 -transparent white -blur 1x1 $@

name_team.png: icons.pdf
	convert icons.pdf[14] -size 480x480 -transparent white -blur 1x1 $@

team_name.png: icons.pdf
	convert icons.pdf[15] -size 480x480 -transparent white -blur 1x1 $@

fullscreen.png: icons.pdf
	convert icons.pdf[16] -size 480x480 -transparent white -blur 1x1 $@

# requires pyqt5-dev-tools
icons.py: resources.qrc $(PICS) battery
	pyrcc5 -o $@ $<
	mv $@ ../webola/

clean:
	rm -rf tex-tmp icons.pdf $(PICS)
