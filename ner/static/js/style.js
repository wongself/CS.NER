var entity;
var str;
var color_per = '#ffcdd2';
var color_loc = '#b3e5fc';
var color_org = '#fff9c4';
var color_none = 'transparent';

var type_task_checked_color = '#FFBF33';
var type_task_unchecked_color = '#FFE084';
var type_method_checked_color = '#B1BA24';
var type_method_unchecked_color = '#E4EA78';
var type_metric_checked_color = '#51C521';
var type_metric_unchecked_color = '#A9ED76';
var type_material_checked_color = '#1B9D96';
var type_material_unchecked_color = '#71E1C7';
var type_other_checked_color = '#1D6EB8';
var type_other_unchecked_color = '#71BBE7';
var type_generic_checked_color = '#AA52E5';
var type_generic_unchecked_color = '#DC97F7';
var type_none_color = 'transparent';

// $('#source_texarea').bind('keypress', function (event) {
//   if (event.keyCode == "13") {
//     $("#query_button").click();
//   }
// })
var target_original_jpredictions

$(function () {
  $('#source_texarea').val('')
  $('#target_texarea').html('')

  // Textarea discription
  $('#source_texarea').bind('input propertychange', function () {
    var $text_src = $('#source_texarea')
    var $text_dst = $('#target_texarea')
    var $text_curr = $('#textarea_statistic_current')
    var $text_src_place = $('#source_texarea_placeholder_text')
    var $text_dst_place = $('#target_texarea_placeholder_text')
    var max_length = 2000
    var text_src_length = $text_src.val().length
    var text_dst_length = $text_dst.text().length
    var text_src_remain = parseInt(max_length - text_src_length)

    if (text_src_length > 0) {
      $text_src_place.css('display', 'none')
      $text_dst_place.css('display', 'none')
    } else {
      if (text_dst_length > 0) {
        $text_src_place.css('display', 'block')
      } else {
        $text_src_place.css('display', 'block')
        $text_dst_place.css('display', 'block')
      }
    }

    if (text_src_remain > 0) {
      $text_curr.html(text_src_length)
    } else {
      $text_curr.html(max_length)
      $text_src.val($text_src.val().substring(0, max_length))
    }
  })

  // Upload document
  $('#upload_doc_button').on('click', function () {
    $('#upload_doc_input').trigger('click')
  });

  $('#upload_doc_input').on('change', function (e) {
    console.log('Document has been imported')
    var doc = e.target.files[0]
    console.log(doc)
  });

  // Export predictions
  $('#export_output_button').on('click', function () {
    if (target_original_jpredictions == null) {
      var $modal = $('#error_happened_modal #modal_error_content')
      $modal.text('No predictions available.')
      $('#error_happened_modal').modal();
      return;
    }
    _export_jpredictions()
  });

  // Type checkbox
  $('.type_checkbox_group .btn').on('click', function (e) {
    // e.stopPropagation()
    // e.preventDefault()
    var class_list = String($(this).attr("class"))
    console.log(class_list)
  });

  $('#type_dropdown_btn').on('click', function () {
    // var $type_inline_group = $('#type_inline_group')
    // var is_dropdown_display = $type_inline_group.css('display')
    // if (is_dropdown_display === 'none') {
    //   $type_inline_group.css('display', 'inline-flex')
    // } else {
    //   $type_inline_group.css('display', 'none')
    // }
  });

  // Recognize entities
  $('#query_button').on('click', function () {
    var $text_src = $('#source_texarea')
    var text_src = $text_src.val();

    if (text_src.length <= 0) {
      var $modal = $('#error_happened_modal #modal_error_content')
      $modal.text('No text or document available.')
      $('#error_happened_modal').modal();
      return;
    }

    $('#query_button').html('\
      <span class="spinner-border spinner-border-sm mr-2" \
        role="status" aria-hidden="true">\
      </span>Recognizing...').addClass('disabled');

    $.ajax({
      type: 'post',
      url: './../entity_query/',
      data: {
        'source': text_src,
        csrfmiddlewaretoken: $('[name="csrfmiddlewaretoken"]').val()
      },
      dataType: 'json',
      success: function (ret) {
        // console.log(ret['jpredictions'])
        var jpredictions = ret['jpredictions']
        target_original_jpredictions = jpredictions
        target_texarea_text = _parse_jpredictions(jpredictions)
        $('#target_texarea').html('')
        $('#target_texarea').html(target_texarea_text)
        $('#query_button').html('Recognize').removeClass('disabled');
      },
      error: function (ret) {
        console.log('error: ' + ret);
        $('#query_button').html('Recognize').removeClass('disabled');
      }
    })
  })
})

function _parse_jpredictions(jpredictions) {
  console.log('Start Parsing')
  // console.log(jpredictions)
  var target_texarea_text = ''
  $.each(jpredictions, function (index, doc) {
    var jtokens = doc['tokens']
    var jentities = doc['entities']
    var index_tokens_type = (new Array(jtokens.length)).fill(1)

    target_texarea_text += '<p>'
    $.each(jentities, function (index, entity) {
      var etype = entity['type']
      var estart = entity['start']
      var eend = entity['end']
      for (let i = estart; i < eend; i++) {
        index_tokens_type[i] *= _get_type_index(etype);
      }
    })
    $.each(jtokens, function (index, token) {
      var tokens_type_color = _get_type_color(index_tokens_type[index])

      if (index && index_tokens_type[index - 1] !== 1) {
        target_texarea_text += '<span class="' + tokens_type_color + '">&nbsp;</span>'
      } else if (index) {
        target_texarea_text += '&nbsp;'
      }

      target_texarea_text += '<span class="' + tokens_type_color + '">' + token + '</span>'
    })
    target_texarea_text += '</p>'
  })
  // console.log(target_texarea_text)
  return target_texarea_text
}

function _get_type_index(type) {
  switch (type) {
    case 'Task':
      return 2
    case 'Method':
      return 3
    case 'Material':
      return 5
    case 'OtherScientificTerm':
      return 7
    case 'Metric':
      return 11
    case 'Generic':
      return 13
    default:
      return 1
  }
}

function _get_type_color(index) {
  switch (index) {
    case 2:
      return 'type-checkbox-task'
    case 3:
      return 'type-checkbox-method'
    case 5:
      return 'type-checkbox-metric'
    case 7:
      return 'type-checkbox-material'
    case 11:
      return 'type-checkbox-other'
    case 13:
      return 'type-checkbox-generic'
    default:
      return 'type-checkbox-none'
  }
}

function _export_jpredictions() {
  var jexport = JSON.stringify(target_original_jpredictions)
  var blob = new Blob([jexport], { type: "text/plain;charset=utf-8" });
  var filename = 'Predictions ' + _generate_timestamp() + '.json'

  var url = window.URL || window.webkitURL;
  link = url.createObjectURL(blob);
  var a = $("<a />");
  a.attr("download", filename);
  a.attr("href", link);
  $("body").append(a);
  a[0].click();
  $("body").remove(a);
}

function _generate_timestamp() {
  var curr_time = new Date().Format("yyyy-MM-dd hh_mm_ss")
  return curr_time
};

function _expand_digit(digit) {
  var digit_expanded
  if (digit >= 1 && digit <= 9) {
    digit_expanded = "0" + digit;
  }
  return digit_expanded
};

Date.prototype.Format = function (fmt) {
  var o = {
    "M+": this.getMonth() + 1,
    "d+": this.getDate(),
    "h+": this.getHours(),
    "m+": this.getMinutes(),
    "s+": this.getSeconds(),
    "q+": Math.floor((this.getMonth() + 3) / 3),
    "S": this.getMilliseconds()
  };
  if (/(y+)/.test(fmt)) fmt = fmt.replace(RegExp.$1, (this.getFullYear() + "").substr(4 - RegExp.$1.length));
  for (var k in o)
    if (new RegExp("(" + k + ")").test(fmt)) fmt = fmt.replace(RegExp.$1, (RegExp.$1.length == 1) ? (o[k]) : (("00" + o[k]).substr(("" + o[k]).length)));
  return fmt;
}

NProgress.configure({ showSpinner: false });

$(document).ajaxStart(function () {
  NProgress.start();
});

$(document).ajaxStop(function () {
  NProgress.done();
});

$("#fsdhkfjhsdkjf").on("change", function (e) {
  var file = e.target.files[0];
  var fileReader = new FileReader();

  fileReader.onload = function () {
    var typedarray = new Uint8Array(this.result);
    getText(typedarray).then(function (text) {
      $("#content").html(text);
    }, function (reason)
    {
      alert('Seems this file is broken, please upload another file');
      console.error(reason);
    });

    //getText() function definition. This is the pdf reader function.
    function getText(typedarray) {

      //PDFJS should be able to read this typedarray content

      var pdf = PDFJS.getDocument(typedarray);
      return pdf.then(function (pdf) {

        // get all pages text
        var maxPages = pdf.pdfInfo.numPages;
        var countPromises = [];
        // collecting all page promises
        for (var j = 1; j <= maxPages; j++) {
          var page = pdf.getPage(j);

          var txt = "";
          countPromises.push(page.then(function (page) {
            // add page promise
            var textContent = page.getTextContent();

            return textContent.then(function (text) {
              // return content promise
              return text.items.map(function (s) {
                return s.str;
              }).join(''); // value page text
            });
          }));
        }

        // Wait for all pages and join text
        return Promise.all(countPromises).then(function (texts) {
          return texts.join('');
        });
      });
    }
  };
  //Read the file as ArrayBuffer
  fileReader.readAsArrayBuffer(file);

});

