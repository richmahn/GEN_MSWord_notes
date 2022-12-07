#!/usr/bin/env python3
#
# TN_MSWrd_to_TSV9_via_Proskomma.py
#
# Copyright (c) 2021 unfoldingWord
# http://creativecommons.org/licenses/MIT/
# See LICENSE file for details.
#
# Contributors:
#   Robert Hunt <Robert.Hunt@unfoldingword.org>
#
# Written Sept 2021 by RJH
#   Last modified: 2021-09-21 by RJH
#
"""
Quick script to create 9-column TN files from MS-Word files.

NOTE: This requires the addition of the OrigQuote column!
"""
from typing import List, Tuple
import sys
import os
import csv
from pathlib import Path
import random
import re
import logging
import subprocess
from collections import OrderedDict
import urllib.request
from usfm_utils import unalign_usfm
from tx_usfm_tools.singleFilelessHtmlRenderer import SingleFilelessHtmlRenderer
from bs4 import BeautifulSoup
import json


LOCAL_SOURCE_FOLDERPATH = 'txt'

# The output folder below must also already exist!
LOCAL_OUTPUT_FOLDERPATH = 'tsv'

BBB_NUMBER_DICT = {'GEN':'01','EXO':'02','LEV':'03','NUM':'04','DEU':'05',
                'JOS':'06','JDG':'07','RUT':'08','1SA':'09','2SA':'10','1KI':'11',
                '2KI':'12','1CH':'13','2CH':'14','EZR':'15',
                'NEH':'16',
                'EST':'17',
                'JOB':'18','PSA':'19','PRO':'20','ECC':'21','SNG':'22','ISA':'23',
                'JER':'24','LAM':'25','EZK':'26','DAN':'27','HOS':'28','JOL':'29',
                'AMO':'30','OBA':'31','JON':'32','MIC':'33','NAM':'34','HAB':'35',
                'ZEP':'36','HAG':'37','ZEC':'38','MAL':'39',
                'MAT':'41','MRK':'42','LUK':'43','JHN':'44','ACT':'45',
                'ROM':'46','1CO':'47','2CO':'48','GAL':'49','EPH':'50','PHP':'51',
                'COL':'52','1TH':'53','2TH':'54','1TI':'55','2TI':'56','TIT':'57',
                'PHM':'58','HEB':'59','JAS':'60','1PE':'61','2PE':'62','1JN':'63',
                '2JN':'64',
                '3JN':'65', 'JUD':'66', 'REV':'67' }

HELPER_PROGRAM_NAME = 'TN_ULT_Quotes_to_OLQuotes.js'


DEBUG_LEVEL = 1

book_data = OrderedDict()
errors = [['line', 'type', 'note']]

def get_book_data():
    response = urllib.request.urlopen("https://git.door43.org/unfoldingWord/en_ult/raw/branch/master/01-GEN.usfm")
    data = response.read()      # a `bytes` object
    book_usfm = data.decode('utf-8') # a `str`; this step can't be used if data is binary
    unaligned_usfm = unalign_usfm(book_usfm)
    book_html, warnings = SingleFilelessHtmlRenderer({"GEN": unaligned_usfm}).render()
    html_verse_splits = re.split(r'(<span id="[^"]+-ch-0*(\d+)-v-(\d+(?:-\d+)?)" class="v-num">)', book_html)
    usfm_chapter_splits = re.split(r'\\c ', unaligned_usfm)
    usfm_verse_splits = None
    chapter_verse_index = 0
    for i in range(1, len(html_verse_splits), 4):
        chapter = html_verse_splits[i+1]
        verses = html_verse_splits[i+2]
        if chapter not in book_data:
            book_data[chapter] = OrderedDict()
            usfm_chapter = f'\\c {usfm_chapter_splits[int(chapter)]}'
            usfm_verse_splits = re.split(r'\\v ', usfm_chapter)
            chapter_verse_index = 0
        chapter_verse_index += 1
        verse_usfm = f'\\v {usfm_verse_splits[chapter_verse_index]}'
        verse_html = html_verse_splits[i] + html_verse_splits[i+3]
        verse_html = re.split('<h2', verse_html)[0]  # remove next chapter since only split on verses
        verse_soup = BeautifulSoup(verse_html, 'html.parser')
        for tag in verse_soup.find_all():
            if (not tag.contents or len(tag.get_text(strip=True)) <= 0) and tag.name not in ['br', 'img']:
                tag.decompose()
        verse_html = str(verse_soup)
        verses = re.findall(r'\d+', verses)
        for verse in verses:
            verse = verse.lstrip('0')
            book_data[chapter][verse] = {
                'usfm': verse_usfm,
                'html': verse_html
            }

def add_error(line:str, type:str, message:str):
    errors.append([line, type, message])


def write_errors():
    with open('errors/errors.tsv', 'w', newline='\n') as csvfile:
        writer = csv.writer(csvfile, delimiter='\t', quotechar='"', lineterminator="\n")
        writer.writerows(errors)

                        
def get_input_fields(input_folderpath:str, BBB:str) -> Tuple[str,str,str,str,str,str]:
    """
    Generator to read the exported MS-Word .txt files
        and return the needed fields.

    Returns a 4-tuple with:
        C,V, (ULT)verseText, (ULT)glQuote, note
    """
    print(f"    Loading {BBB} TN links from MS-Word exported text file…")
    input_filepath = os.path.join(input_folderpath, f'{BBB}.txt')
    Bbb = BBB[0] + BBB[1].lower() + BBB[2].lower()
    C = V = '0'
    verseText = glQuote = note = ''
    occurrence = 0
    occurrences = {}
    with open(input_filepath, 'rt', encoding='utf-8') as input_text_file:
        prevLine = ''
        for line_number, line in enumerate(input_text_file, start=1):
            if line_number == 1 and line.startswith('\ufeff'):
                line = line[1:]  # Remove optional BOM
            line = line.rstrip('\n\r').strip().replace("\xa0", " ")

            if line.isdigit():
                print("LINE IS DIGIT!!! ", line)
                newC = line
                if int(line) != int(C)+1:
                    add_error(line_number, 'file', f"Chapter number is not increasing as expected: moving from {C} to {newC}")
                V = '0'
                C = newC
                glQuote = note = verseText = ''
                prevLine = line
                continue
            
            if line.startswith(f'{Bbb} {C}:'):
                parts = line.split(' ')
                print(parts)
                newV = parts[1].split(':')[1]
                print(line)
                print(newV, V)
                if int(newV) != int(V)+1:
                    add_error(line_number, "file", f"Verse number is not increasing as expected: moving from {V} to {newV}")
                V = newV
                verseText = ' '.join(parts[2:])
                print(f"|{verseText}|")
                print(book_data[C][V])
                text = re.sub('<[^<]+?>', '', book_data[C][V]['html']).strip()
                text = re.sub('^\d+ *', '', text)
                text = re.sub(r'\s+', ' ', text)
                print(f"?{text}?")
                verseText = re.sub(r'\s+', ' ', verseText)
                if verseText not in text:
                    add_error(line_number, "verse", f"{BBB} {C}:{V}: Verse should read:\n> {text}\n\nNOT\n> {verseText}")
                occurrences = {}
                glQuote = note = ''
                prevLine = line
                continue

            if not line or 'Paragraph Break' in line or line.startswith(f'{C}:') or prevLine.startswith(f'{C}:'):
                if glQuote and note:
                    yield C, V, verseText, glQuote, str(occurrence), note
                glQuote = note = ''
                occurrence = 0
                prevLine = line
                continue
            
            if glQuote:
                if note:
                    note += " "
                note += line
                prevLine = line
                continue

            glQuote = line
            quote_count = len(re.findall(r'(?<![^\W_])' + re.escape(glQuote) + r'(?![^\W_])', text))
            if quote_count == 0:
                add_error(line_number, "glQuote", f'{Bbb} {C}:{V}: GL Quote not found:\n```\n{glQuote}\n```\nnot in\n\n> {text}')
            else:
                words = glQuote.split(' ')
                words_str = ''
                for word in words:
                    if words_str:
                        words_str += ' '
                    words_str += word
                    if words_str not in occurrences:
                        occurrences[words_str] = 1
                    else:
                        occurrences[words_str] += 1
                occurrence = occurrences[glQuote]
                if quote_count < occurrence:
                    occurrence = quote_count
            prevLine = line
            continue

    # if errors['glQuotres']:
    #     print("Please fix GL quotes so they match and try again.")
    #     sys.exit(1)
    
    if glQuote and note:
        yield C, V, verseText, glQuote, str(occurrence), note
# end of get_input_fields function


OrigL_QUOTE_PLACEHOLDER = "NO OrigLQuote AVAILABLE!!!"
def convert_MSWrd_TN_TSV(input_folderpath:str, output_folderpath:str, BBB:str, nn:str) -> int:
    """
    Function to read the exported .txt file from MS-Word and write the TN markdown file.

    Returns the number of unique GLQuotes that were written in the call.
    """
    testament = 'OT' if int(nn)<40 else 'NT'
    output_filepath = os.path.join(output_folderpath, f'en_tn_{nn}-{BBB}.tsv')
    temp_output_filepath = Path(f"{output_filepath}.tmp")
    with open(temp_output_filepath, 'wt', encoding='utf-8') as temp_output_TSV_file:
        previously_generated_ids:List[str] = [''] # We make ours unique per file (spec only used to say unique per verse)
        temp_output_TSV_file.write('Book\tChapter\tVerse\tID\tSupportReference\tOrigQuote\tOccurrence\tGLQuote\tOccurrenceNote\n')
        for line_count, (C, V, verse_text, gl_quote, occurrence, note) in enumerate(get_input_fields(input_folderpath, BBB), start=1):
            # print(f"Got {BBB} {C}:{V} '{note}' for '{gl_quote}' {occurrence} in: {verse_text}")

            generated_id = ''
            while generated_id in previously_generated_ids:
                generated_id = random.choice('abcdefghijklmnopqrstuvwxyz') + random.choice('abcdefghijklmnopqrstuvwxyz0123456789') + random.choice('abcdefghijklmnopqrstuvwxyz0123456789') + random.choice('abcdefghijklmnopqrstuvwxyz0123456789')
            previously_generated_ids.append(generated_id)

            support_reference = ''
            orig_quote = OrigL_QUOTE_PLACEHOLDER

            # Find "See:" TA refs and process them -- should only be one
            for match in re.finditer(r'\(See: ([-A-Za-z0-9]+?)\)', note):
                if support_reference:
                    add_error("-1", "format", f"{BBB} {C}:{V}: Should only be one TA ref: {note}")
                support_reference = match.group(1)
                note = f"{note[:match.start()]}(See: [[rc://en/ta/man/translate/{support_reference}]]){note[match.end():]}"

            gl_quote = gl_quote.strip()
            if (gl_quote.startswith('"')): gl_quote = f'“{gl_quote[1:]}'
            if (gl_quote.endswith('"')): gl_quote = f'{gl_quote[:-1]}”'
            if (gl_quote.startswith("'")): gl_quote = f'‘{gl_quote[1:]}'
            if (gl_quote.endswith("'")): gl_quote = f'{gl_quote[:-1]}’'
            gl_quote = gl_quote.replace('" ', '” ').replace(' "', ' “').replace("' ", '’ ').replace(" '", ' ‘').replace("'s", '’s')
            if '"' in gl_quote or "'" in gl_quote:
                add_error(line_number, "format", f"{BBB} {C}:{V}: glQuote still has straight quote marks: '{gl_quote}'")

            note = note.strip()
            if (note.startswith('"')): note = f'“{note[1:]}'
            if (note.endswith('"')): note = f'{note[:-1]}”'
            note = note.replace('" ', '” ').replace(' "', ' “') \
                .replace('".', '”.').replace('",', '”,') \
                .replace('("', '(“').replace('")', '”)') \
                .replace("' ", '’ ').replace(" '", ' ‘').replace("'s", '’s')
            if '"' in note or "'" in note:
                add_error("-1", "format", f"{BBB} {C}:{V}: note still has straight quote marks: '{note}'")

            temp_output_TSV_file.write(f'{BBB}\t{C}\t{V}\t{generated_id}\t{support_reference}\t{orig_quote}\t{occurrence}\t{gl_quote}\t{note}\n')

    # Now use Proskomma to find the ULT GLQuote fields for the OrigQuotes in the temporary outputted file
    print(f"      Running Proskomma to find OrigL quotes for {testament} {BBB}… (might take a few minutes)")
    
    completed_process_result = subprocess.run(['node', HELPER_PROGRAM_NAME, temp_output_filepath, testament], capture_output=True)
    # print(f"Proskomma {BBB} result was: {completed_process_result}")
    if completed_process_result.returncode:
        print(f"      Proskomma {BBB} ERROR result was: {completed_process_result.returncode}")
    if completed_process_result.stderr:
        print(f"      Proskomma {BBB} error output was:\n{completed_process_result.stderr.decode()}")
    proskomma_output_string = completed_process_result.stdout.decode()
    # print(f"Proskomma {BBB} output was: {proskomma_output_string}") # For debugging JS helper program only
    output_lines = proskomma_output_string.split('\n')
    if output_lines:
        # Log any errors that occurred -- not really needed now coz they go to stderr
        print_next_line_counter = 0
        for output_line in output_lines:
            if 'Error:' in output_line:
                logging.error(output_line)
                print_next_line_counter = 2 # Log this many following lines as well
            elif print_next_line_counter > 0:
                logging.error(output_line)
                print_next_line_counter -= 1
        print(f"      Proskomma got: {' / '.join(output_lines[:9])}") # Displays the UHB/UGNT and ULT loading times
        print(f"        Proskomma did: {output_lines[-2]}")
    else: logging.critical("No output from Proskomma!!!")
    # Put the GL Quotes into a dict for easy access
    match_dict = {}
    for match in re.finditer(r'(\w{3})_(\d{1,3}):(\d{1,3}) ►(.+?)◄ “(.+?)”', proskomma_output_string):
        B, C, V, gl_quote, orig_quote = match.groups()
        assert B == BBB, f"{B} {C}:{V} '{orig_quote}' Should be equal '{B}' '{BBB}'"
        if orig_quote:
            match_dict[(C,V,gl_quote)] = orig_quote
        else:
            logging.error(f"{B} {C}:{V} '{gl_quote}' Should have gotten an OrigLQuote")
    print(f"        Got {len(match_dict):,} unique OrigL Quotes back from Proskomma for {BBB}")

    match_count = fail_count = 0
    if match_dict: # (if not, the ULT book probably isn't aligned yet)
        # Now put the OrigL Quotes into the file
        with open(temp_output_filepath, 'rt', encoding="utf-8") as temp_input_text_file:
            with open(output_filepath, 'wt', encoding='utf-8') as output_TSV_file:
                output_TSV_file.write(temp_input_text_file.readline()) # Write the TSV header
                for line in temp_input_text_file:
                    B, C, V, rowID, support_reference, orig_quote, occurrence, gl_quote, occurrence_note = line.split('\t')
                    try:
                        if gl_quote:
                            orig_quote = match_dict[(C,V,gl_quote)]
                            match_count += 1
                    except KeyError:
                        logging.error(f"Unable to find OrigLQuote for {BBB} {C}:{V} {rowID} '{gl_quote}'")
                        fail_count += 1
                    # orig_quote = orig_quote.replace('…',' … ').replace('  ',' ') # Put space around ellipsis in field intended for human readers
                    output_TSV_file.write(f'{B}\t{C}\t{V}\t{rowID}\t{support_reference}\t{orig_quote}\t{occurrence}\t{gl_quote}\t{occurrence_note}')

    os.remove(temp_output_filepath)

    return line_count, match_count, fail_count
# end of convert_TN_TSV


def main():
    """
    Go through the list of Bible books
        and convert them
        while keeping track of some basic statistics
    """
    print("TN_MSWrd_to_TSV9_via_Proskomma.py")
    print(f"  Source folderpath is {LOCAL_SOURCE_FOLDERPATH}/")
    print(f"  Output folderpath is {LOCAL_OUTPUT_FOLDERPATH}/")
    total_files_read = total_files_written = 0
    total_lines_read = total_quotes_written = 0
    total_GLQuote_failures = 0
    failed_book_list = []
    for BBB, nn in BBB_NUMBER_DICT.items():
        if BBB != 'GEN': continue # Just process this one book
        # if BBB not in ('MAT','MRK','LUK','JHN', 'ACT',
        #                 'ROM','1CO','2CO','GAL','EPH','PHP','COL',
        #                 '1TH','2TH','1TI','2TI','TIT','PHM',
        #                 'HEB','JAS','1PE','2PE','1JN','2JN','3JN','JUD','REV'):
        #     continue # Just process NT books
        lines_read, this_note_count, fail_count = convert_MSWrd_TN_TSV(LOCAL_SOURCE_FOLDERPATH, LOCAL_OUTPUT_FOLDERPATH, BBB, nn)
        total_lines_read += lines_read
        total_files_read += 1
        if this_note_count:
            total_quotes_written += this_note_count
            total_files_written += 1
        total_GLQuote_failures += fail_count
    print(f"  {total_lines_read:,} lines read from {total_files_read} TSV file{'' if total_files_read==1 else 's'}")
    print(f"  {total_quotes_written:,} GL quotes written to {total_files_written} TSV file{'' if total_files_written==1 else 's'} in {LOCAL_OUTPUT_FOLDERPATH}/")
    if total_GLQuote_failures:
        print(f"  Had a total of {total_GLQuote_failures:,} GLQuote failure{'' if total_GLQuote_failures==1 else 's'}!")
    if failed_book_list:
        logging.critical(f"{len(failed_book_list)} books failed completely: {failed_book_list}")
# end of main function

if __name__ == '__main__':
    get_book_data()
    main()
    write_errors()
# end of TN_MSWrd_to_TSV9_via_Proskomma.py
