TAPES := $(wildcard *.tape)
GIFS  := $(TAPES:.tape=.gif)

all: $(GIFS)

%.gif: %.tape
	vhs $<

clean:
	rm -f *.gif

.PHONY: all clean
