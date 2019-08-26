var Moonsheep = {
  init: function(){
    console.log('MOONSHEEP RISING...');
    this.progressBar();
    this.menuToggle();
  },

  /** Init width of prog bars **/
  progressBar: function(){
    console.log('1. Progress Bar calculations...');
    $('.progress-bar').each(function(i){
      var w = $(this).data('width');
      var t = $(this).next('.progress-number');

      $(this).css('width', w + '%');
      t.text(w + '%');
      if(w > 45){
        t.css('color', '#FFFEE7');
      }
      else {
        t.css('color', '#644263');
      }
    });
  },

  menuToggle: function(){
    $('.menu-toggle').click(function(e){
      e.preventDefault();
      var target = $(this).data('target');
      if($(target).is(':visible')){
        $(this).removeClass('close');
        $(target).removeClass('show').addClass('hide');
      }
      else {
        $(this).addClass('close');
        $(target).removeClass('hide').addClass('show');
      }
    });
  }
}

$(document).ready(function(){
  Moonsheep.init();
});
