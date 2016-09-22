function getentry(dictionaryurl,searchterm) {
    $.getJSON('/'+dictionaryurl+'?entry='+searchterm, function (entryreturned) {
        var dLen = entryreturned.length;
        var entries = [];
        var subheadings = ['word','head','senses','summary'];
        for (i = 0; i < dLen; i++) {
            var thisentry = '';

            // each entry is itself a collection of items some of which contain still further items
            // the summaries contain 'sns', 'auth', and 'quot' lists
                for (sh in subheadings) {
                    thisentry += '<p class="'+subheadings[sh]+'>'+subheadings[sh]+'</p>\n<p class="'+subheadings[sh]+'>';
                    for (j = 0; j<entries[i][subheadings[sh]].length; j++){
                        thisentry += entries[i][subheadings[sh]][j]+'<br />\n';
                        }
                    }
            }
            entries.push(thisentry);

        $("#lexicadialogtext").html(entries);
        $("#lexicadialog").show();
    });
}

