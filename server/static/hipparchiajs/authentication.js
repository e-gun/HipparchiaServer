$('#validateusers').dialog({ autoOpen: false });

$('#executelogin').click( function() {
    $('#validateusers').dialog( 'open' );
});

$('#executelogout').click( function() {
    $.getJSON('/authentication/logout', function(data){
         $('#userid').html(data);
    });
    $('#executelogout').hide();
    $('#executelogin').show();
});
