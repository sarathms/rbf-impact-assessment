/*
 *    OpenERP, Open Source Management Solution
 *    Copyright (C) 2004-TODAY OpenERP S.A. <http://www.openerp.com>
 *
 *    This program is free software: you can redistribute it and/or modify
 *    it under the terms of the GNU Affero General Public License as
 *    published by the Free Software Foundation, either version 3 of the
 *    License, or (at your option) any later version.
 *
 *    This program is distributed in the hope that it will be useful,
 *    but WITHOUT ANY WARRANTY; without even the implied warranty of
 *    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 *    GNU Affero General Public License for more details.
 *
 *    You should have received a copy of the GNU Affero General Public License
 *    along with this program.  If not, see <http://www.gnu.org/licenses/>.
 */

/*
 * This file is intended to add interactivity to ia forms rendered by
 * the website engine.
 */

$(document).ready(function () {
    'use strict';

    console.debug("[ia] Custom JS for ia is loading...");

    var the_form = $('.js_iaform');
    var prefill_controller = the_form.attr("data-prefill");
    var validate_controller = the_form.attr("data-validate");
    var submit_controller = the_form.attr("data-submit");
    var scores_controller = the_form.attr("data-scores");
    var print_mode = false;
    var quiz_correction_mode = false;

    // Printing mode: will disable all the controls in the form
    if (_.isUndefined(submit_controller)) {
        $('.js_iaform :input').prop('disabled', true);
        print_mode = true;
    }

    // Quizz correction mode
    if (! _.isUndefined(scores_controller)) {
        quiz_correction_mode = true;
    }

    // Custom code for right behavior of radio buttons with comments box
    $('.js_comments>input[type="text"]').focusin(function(){
        $(this).prev().find('>input').attr("checked","checked");
    });
    $('.js_radio input[type="radio"][data-oe-ia-otherr!="1"]').click(function(){
        $(this).closest('.js_radio').find('.js_comments>input[type="text"]').val("");
    });
    $('.js_comments input[type="radio"]').click(function(){
        $(this).closest('.js_comments').find('>input[data-oe-ia-othert="1"]').focus();
    });
    // Custom code for right behavior of dropdown menu with comments
    $('.js_drop input[data-oe-ia-othert="1"]').hide();
    $('.js_drop select').change(function(){
        var other_val = $(this).find('.js_other_option').val();
        if($(this).val() === other_val){
            $(this).parent().removeClass('col-md-12').addClass('col-md-6');
            $(this).closest('.js_drop').find('input[data-oe-ia-othert="1"]').show().focus();
        }
        else{
            $(this).parent().removeClass('col-md-6').addClass('col-md-12');
            $(this).closest('.js_drop').find('input[data-oe-ia-othert="1"]').val("").hide();
        }
    });
    // Custom code for right behavior of checkboxes with comments box
    $('.js_ck_comments>input[type="text"]').focusin(function(){
        $(this).prev().find('>input').attr("checked","checked");
    });
    $('.js_ck_comments input[type="checkbox"]').change(function(){
        if (! $(this).prop("checked")){
            $(this).closest('.js_ck_comments').find('input[type="text"]').val("");
        }
    });

    // Pre-filling of the form with previous answers
    function prefill(){
        var prefill_def = $.ajax(prefill_controller, {dataType: "json"})
            .done(function(json_data){
                _.each(json_data, function(value, key){
                    the_form.find(".form-control[name=" + key + "]").val(value);
                    the_form.find("input[name^=" + key + "]").each(function(){
                        $(this).val(value);
                    });
                });
            })
            .fail(function(){
                console.warn("[ia] Unable to load prefill data");
            });
        return prefill_def;
    }

    // Display score if quiz correction mode
    function display_scores(){
        var score_def = $.ajax(scores_controller, {dataType: "json"})
            .done(function(json_data){
                _.each(json_data, function(value, key){
                    the_form.find("span[data-score-question=" + key + "]").text("Your score: " + value);
                });
            })
            .fail(function(){
                console.warn("[ia] Unable to load score data");
            });
        return score_def;
    }

    // Parameters for form submission
    $('.js_iaform').ajaxForm({
        url: submit_controller,
        type: 'POST',                       // submission type
        dataType: 'json',                   // answer expected type
        beforeSubmit: function(){           // hide previous errmsg before resubmitting
            $('.js_errzone').html("").hide();
        },
        success: function(response, status, xhr, wfe){ // submission attempt
            if(_.has(response, 'errors')){  // some questions have errors
                _.each(_.keys(response.errors), function(key){
                    $("#" + key + '>.js_errzone').append('<p>' + response.errors[key] + '</p>').show();
                });
                return false;
            }
            else if (_.has(response, 'redirect')){      // form is ok
                window.location.replace(response.redirect);
                return true;
            }
            else {                                      // server sends bad data
                console.error("Incorrect answer sent by server");
                return false;
            }
        },
        timeout: 5000,
        error: function(jqXHR, textStatus, errorThrown){ // failure of AJAX request
            $('#AJAXErrorModal').modal('show');
        }
    });

    // // Handles the event when a question is focused out
    // $('.js_question-wrapper').focusout(
    //     function(){
    //         console.debug("[ia] Focus lost on question " + $(this).attr("id"));
    // });

    // Launch prefilling
    prefill();
    if(quiz_correction_mode === true){
        display_scores();
    }

    console.debug("[ia] Custom JS for ia loaded!");
});
