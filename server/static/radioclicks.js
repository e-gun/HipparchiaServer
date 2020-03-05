//
//	HipparchiaServer: an interface to a database of Greek and Latin texts
//	Copyright: E Gunderson 2016-20
//	License: License: GNU GENERAL PUBLIC LICENSE 3
//      (see LICENSE in the top level directory of the distribution)

//
// the radio ui-click options
//

$('#headwordindexing_y').click( function(){
    setoptions('headwordindexing', 'yes'); $('#headwordindexingactive').show(); $('#headwordindexinginactive').hide();
});

$('#headwordindexing_n').click( function(){
    setoptions('headwordindexing', 'no'); $('#headwordindexinginactive').show(); $('#headwordindexingactive').hide();
});

$('#frequencyindexing_y').click( function(){
    setoptions('indexbyfrequency', 'yes'); $('#frequencyindexingactive').show(); $('#frequencyindexinginactive').hide();
});

$('#frequencyindexing_n').click( function(){
    setoptions('indexbyfrequency', 'no'); $('#frequencyindexinginactive').show(); $('#frequencyindexingactive').hide();
});


$('#onehit_y').click( function(){
    setoptions('onehit', 'yes'); $('#onehitistrue').show(); $('#onehitisfalse').hide();
});

$('#onehit_n').click( function(){
    setoptions('onehit', 'no'); $('#onehitisfalse').show(); $('#onehitistrue').hide();
});

$('#autofillinput').click( function(){
    setoptions('rawinputstyle', 'no'); $('#usingautoinput').show(); $('#usingrawinput').hide();
    let elementarray = ['#rawlocationinput', '#rawendpointinput', '#fromnotice', '#endpointnotice',
        '#endpointbutton-isopen', '#endpointbutton-isclosed', '#rawlocationinput', '#rawendpointinput'];
    bulkhider(elementarray);
});

$('#manualinput').click( function(){
    setoptions('rawinputstyle', 'yes'); $('#usingrawinput').show(); $('#usingautoinput').hide();
    let elementarray = ['#level05endpoint', '#level04endpoint', '#level03endpoint', '#level02endpoint', '#level01endpoint',
        '#level00endpoint', '#level05', '#level04', '#level03', '#level02', '#level01', '#level00' ];
    bulkhider(elementarray);
});

$('#includespuria').change(function() {
    if(this.checked) { setoptions('spuria', 'yes'); } else { setoptions('spuria', 'no'); }
    refreshselections();
    loadoptions();
    });

$('#includevaria').change(function() {
    if(this.checked) { setoptions('varia', 'yes'); } else { setoptions('varia', 'no'); }
    refreshselections();
    loadoptions();
    });

$('#includeincerta').change(function() {
    if(this.checked) { setoptions('incerta', 'yes'); } else { setoptions('incerta', 'no'); }
    refreshselections();
    loadoptions();
    });

$('#greekcorpus').change(function() {
    if(this.checked) { setoptions('greekcorpus', 'yes'); } else { setoptions('greekcorpus', 'no'); }
    refreshselections();
    loadoptions();
    });

$('#latincorpus').change(function() {
    if(this.checked) { setoptions('latincorpus', 'yes'); } else { setoptions('latincorpus', 'no'); }
    refreshselections();
    loadoptions();
    });

$('#inscriptioncorpus').change(function() {
    if(this.checked) { setoptions('inscriptioncorpus', 'yes'); } else { setoptions('inscriptioncorpus', 'no'); }
    refreshselections();
    loadoptions();
    });

$('#papyruscorpus').change(function() {
    if(this.checked) { setoptions('papyruscorpus', 'yes'); } else { setoptions('papyruscorpus', 'no'); }
    refreshselections();
    loadoptions();
    });

$('#christiancorpus').change(function() {
    if(this.checked) { setoptions('christiancorpus', 'yes'); } else { setoptions('christiancorpus', 'no'); }
    refreshselections();
    loadoptions();
    });

$('#sensesummary').change(function() {
    if(this.checked) { setoptions('sensesummary', 'yes'); } else { setoptions('sensesummary', 'no'); }
    refreshselections();
    loadoptions();
    });

$('#authorssummary').change(function() {
    if(this.checked) { setoptions('authorssummary', 'yes'); } else { setoptions('authorssummary', 'no'); }
    refreshselections();
    loadoptions();
    });

$('#quotesummary').change(function() {
    if(this.checked) { setoptions('quotesummary', 'yes'); } else { setoptions('quotesummary', 'no'); }
    refreshselections();
    loadoptions();
    });

$('#bracketsquare').change(function() {
    if(this.checked) { setoptions('bracketsquare', 'yes'); } else { setoptions('bracketsquare', 'no');}
    refreshselections();
    loadoptions();
    });

$('#bracketround').change(function() {
    if(this.checked) { setoptions('bracketround', 'yes'); } else { setoptions('bracketround', 'no'); }
    refreshselections();
    loadoptions();
    });

$('#bracketangled').change(function() {
    if(this.checked) { setoptions('bracketangled', 'yes'); } else { setoptions('bracketangled', 'no'); }
    refreshselections();
    loadoptions();
    });

$('#bracketcurly').change(function() {
    if(this.checked) { setoptions('bracketcurly', 'yes'); } else { setoptions('bracketcurly', 'no'); }
    refreshselections();
    loadoptions();
    });

$('#debughtml').change(function() {
    if(this.checked) { setoptions('debughtml', 'yes'); } else { setoptions('debughtml', 'no'); }
    refreshselections();
    loadoptions();
    });

$('#debugdb').change(function() {
    if(this.checked) { setoptions('debugdb', 'yes'); } else { setoptions('debugdb', 'no'); }
    refreshselections();
    loadoptions();
    });

$('#debuglex').change(function() {
    if(this.checked) { setoptions('debuglex', 'yes'); } else { setoptions('debuglex', 'no'); }
    refreshselections();
    loadoptions();
    });

$('#debugparse').change(function() {
    if(this.checked) { setoptions('debugparse', 'yes'); } else { setoptions('debugparse', 'no'); }
    refreshselections();
    loadoptions();
    });

$('#indexskipsknownwords').change(function() {
    if(this.checked) { setoptions('indexskipsknownwords', 'yes'); } else { setoptions('indexskipsknownwords', 'no'); }
    refreshselections();
    loadoptions();
    });

$('#searchinsidemarkup').change(function() {
    if(this.checked) { setoptions('searchinsidemarkup', 'yes'); } else { setoptions('searchinsidemarkup', 'no'); }
    refreshselections();
    loadoptions();
    });

$('#zaplunates').change(function() {
    if(this.checked) { setoptions('zaplunates', 'yes'); } else { setoptions('zaplunates', 'no'); }
    refreshselections();
    loadoptions();
    });

$('#zapvees').change(function() {
    if(this.checked) { setoptions('zapvees', 'yes'); } else { setoptions('zapvees', 'no'); }
    refreshselections();
    loadoptions();
    });

$('#suppresscolors').change(function() {
    if(this.checked) { setoptions('suppresscolors', 'yes'); } else { setoptions('suppresscolors', 'no'); }
    refreshselections();
    loadoptions();
    window.location.href = '/';
    });

$('#simpletextoutput').change(function() {
    if(this.checked) { setoptions('simpletextoutput', 'yes'); } else { setoptions('simpletextoutput', 'no'); }
    refreshselections();
    loadoptions();
    });

$('#principleparts').change(function() {
    if(this.checked) { setoptions('principleparts', 'yes'); } else { setoptions('principleparts', 'no'); }
    if(this.checked) { $('#mophologytablesoptions').show(); } else { $('#mophologytablesoptions').hide(); }
    refreshselections();
    loadoptions();
    });

$('#showwordcounts').change(function() {
    if(this.checked) { setoptions('showwordcounts', 'yes'); } else { setoptions('showwordcounts', 'no'); }
    refreshselections();
    loadoptions();
    });

$('#morphdialects').change(function() {
    if(this.checked) { setoptions('morphdialects', 'yes'); } else { setoptions('morphdialects', 'no'); }
    refreshselections();
    loadoptions();
    });

$('#morphduals').change(function() {
    if(this.checked) { setoptions('morphduals', 'yes'); } else { setoptions('morphduals', 'no'); }
    refreshselections();
    loadoptions();
    });

$('#morphemptyrows').change(function() {
    if(this.checked) { setoptions('morphemptyrows', 'yes'); } else { setoptions('morphemptyrows', 'no'); }
    refreshselections();
    loadoptions();
    });

$('#morphimper').change(function() {
    if(this.checked) { setoptions('morphimper', 'yes'); } else { setoptions('morphimper', 'no'); }
    refreshselections();
    loadoptions();
    });

$('#morphinfin').change(function() {
    if(this.checked) { setoptions('morphinfin', 'yes'); } else { setoptions('morphinfin', 'no'); }
    refreshselections();
    loadoptions();
    });

$('#morphfinite').change(function() {
    if(this.checked) { setoptions('morphfinite', 'yes'); } else { setoptions('morphfinite', 'no'); }
    refreshselections();
    loadoptions();
    });

$('#morphpcpls').change(function() {
    if(this.checked) { setoptions('morphpcpls', 'yes'); } else { setoptions('morphpcpls', 'no'); }
    refreshselections();
    loadoptions();
    });

$('#morphtables').change(function() {
    if(this.checked) { setoptions('morphtables', 'yes'); } else { setoptions('morphtables', 'no'); }
    refreshselections();
    loadoptions();
    });

$('#collapseattic').change(function() {
    if(this.checked) { setoptions('collapseattic', 'yes'); } else { setoptions('collapseattic', 'no'); }
    refreshselections();
    loadoptions();
    });