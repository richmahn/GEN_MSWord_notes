#!/usr/bin/env bash

sex -e

if [ -e "txt/GEN.txt" ]; then
	rm txt/GEN.txt
fi

for i in {1..50}
do
	DOCX="Notes Gen $i.docx"
	if [ -f "$DOCX" ]; then
    echo "$DOCX exists."
		TEXT="Notes Gen $i.txt"
		if [ -f "$TEXT" ]; then
			rm "$TEXT"
		fi
		./docx2txt.sh "$DOCX"
		echo $TEXT
		echo $DOCX
		if [ -f "$TEXT" ]; then
			echo "Adding $DOCX"
			cat "$TEXT" >> txt/GEN.txt
		fi
  fi
done
