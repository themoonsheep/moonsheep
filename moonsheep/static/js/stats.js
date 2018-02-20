$(document).ready(function () {
  $.ajax({
    type: "get",
    url: "http://localhost:5000/api/project/1?",
    success: function (result) {
      console.log(result);
    },
    error: function (cb) {
      console.log(cb);
    }
  });
});