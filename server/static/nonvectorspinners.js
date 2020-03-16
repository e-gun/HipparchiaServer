//
//	HipparchiaServer: an interface to a database of Greek and Latin texts
//	Copyright: E Gunderson 2016-20
//	License: License: GNU GENERAL PUBLIC LICENSE 3
//      (see LICENSE in the top level directory of the distribution)

//
// non-vector spinners
//

$('#linesofcontextspinner').spinner({
    max: 20,
    min: 0,
    value: 2,
    step: 2,
    stop: function( event, ui ) {
        let result = $('#linesofcontextspinner').spinner('value');
        setoptions('linesofcontext', String(result));
        },
    spin: function( event, ui ) {
        let result = $('#linesofcontextspinner').spinner('value');
        setoptions('linesofcontext', String(result));
        }
        });

$('#browserspinner').spinner({
    max: 50,
    min: 5,
    value: 1,
    stop: function( event, ui ) {
        let result = $('#browserspinner').spinner('value');
        setoptions('browsercontext', String(result));
        },
    spin: function( event, ui ) {
        let result = $('#browserspinner').spinner('value');
        setoptions('browsercontext', String(result));
        }
        });

$( '#hitlimitspinner' ).spinner({
    min: 1,
    value: 1000,
    step: 50,
    stop: function( event, ui ) {
        let result = $('#hitlimitspinner').spinner('value');
        setoptions('maxresults', String(result));
        },
    spin: function( event, ui ) {
        let result = $('#hitlimitspinner').spinner('value');
        setoptions('maxresults', String(result));
        }
        });

$( '#latestdate' ).spinner({
    min: -850,
    max: 1500,
    value: 1500,
    step: 50,
    stop: function( event, ui ) {
        let result = $('#latestdate').spinner('value');
        setoptions('latestdate', String(result));
        refreshselections();
        },
    spin: function( event, ui ) {
        let result = $('#latestdate').spinner('value');
        setoptions('latestdate', String(result));
        refreshselections();
        }
        });


$( '#earliestdate' ).spinner({
    min: -850,
    max: 1500,
    value: -850,
    step: 50,
    stop: function( event, ui ) {
        let result = $('#earliestdate').spinner('value');
        setoptions('earliestdate', String(result));
        refreshselections();
        },
    spin: function( event, ui ) {
        let result = $('#earliestdate').spinner('value');
        setoptions('earliestdate', String(result));
        refreshselections();
        }
        });


// 'width' property not working when you define the spinners
for (let i = 0; i < nonvectorspinners.length; i++) {
    const mywidth = 90;
    $(nonvectorspinners[i]).width(mywidth);
}

