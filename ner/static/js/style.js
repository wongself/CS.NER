var entity;
var str;
var color_per = '#ffcdd2';
var color_loc = '#b3e5fc';
var color_org = '#fff9c4';
var color_none = 'transparent';
$(function () {
  $('#query_button').click(function () {
    str = $('#input_string').val();
    if (str == '') {
      $('#source_check_modal').modal();
      return;
    }
    $('#result').html('\
        <div class="d-flex align-items-center">\
          <strong>加载中...</strong>\
          <div class="spinner-border text-light ml-auto" role="status" aria-hidden="true"></div>\
        </div>');
    $('#query_button').html('\
        <span class="spinner-border spinner-border-sm mr-2" \
          role="status" aria-hidden="true">\
        </span>识别中...').addClass('disabled');
    queryData = { 'keyword': str };
    queryData['csrfmiddlewaretoken'] = '{{ csrf_token }}';
    $.ajax({
      url: './../entity_query',
      type: 'post',
      data: queryData,
      success: function (ret) {
        console.log(ret);
        $('#result').text(str)
        entity = ret['entity'];
        change_color();
        $('#display-card').removeClass().addClass('pulse animated').one('webkitAnimationEnd mozAnimationEnd MSAnimationEnd oanimationend animationend', function () {
          $(this).removeClass();
        });
        $('#query_button').html('<span class="button-text">识别</span>').removeClass('disabled');
      },
      error: function (ret) {
        console.log(ret);
        $('#query_button').html('<span class="button-text">识别</span>').removeClass('disabled');
      }
    })
  })
})

function set_color(per, loc, org) {
  function showEntity(key, mode) {
    var color;
    if (mode == 'LOC') {
      color = loc;
    }
    else if (mode == 'PER') {
      color = per;
    }
    else if (mode == 'ORG') {
      color = org;
    }
    return '<span style="background-color: ' + color + '">' + key + '</span>';
  }

  if (entity == undefined || str == undefined) {
    return '';
  }

  var html = '';
  var tmp;
  for (var i = 0; i < str.length; i++) {
    if (entity[i] == 'B-LOC' || entity[i] == 'I-LOC') {
      tmp = showEntity(str[i], 'LOC');
    }
    else if (entity[i] == 'B-PER' || entity[i] == 'I-PER') {
      tmp = showEntity(str[i], 'PER');
    }
    else if (entity[i] == 'B-ORG' || entity[i] == 'I-ORG') {
      tmp = showEntity(str[i], 'ORG');
    }
    else {
      tmp = str[i];
    }
    html += tmp;
  }
  return html;
}

function change_color() {
  console.log('change_color')
  var loc, org, per;
  if ($("#checkbox_per").is(":checked"))
    per = color_per;
  else
    per = color_none;

  if ($("#checkbox_loc").is(":checked"))
    loc = color_loc;
  else
    loc = color_none;

  console.log($("#checkbox_org").is(":checked"))
  if ($("#checkbox_org").is(":checked"))
    org = color_org;
  else
    org = color_none;
  console.log(org)

  var result = document.getElementById('result');
  result.innerHTML = set_color(per, loc, org);
}

$('#input_string').bind('keypress', function (event) {
  if (event.keyCode == "13") {
    $("#query_button").click();
  }
})
NProgress.configure({ showSpinner: false });
$(document).ajaxStart(function () {
  NProgress.start();
});
$(document).ajaxStop(function () {
  NProgress.done();
});