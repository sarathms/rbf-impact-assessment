# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2013-Today OpenERP SA (<http://www.openerp.com>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import json
import logging
import werkzeug
import werkzeug.utils
from datetime import datetime
from math import ceil

from openerp import SUPERUSER_ID
from openerp.addons.web import http
from openerp.addons.web.http import request
from openerp.tools.misc import DEFAULT_SERVER_DATETIME_FORMAT as DTF
from openerp.tools.safe_eval import safe_eval


_logger = logging.getLogger(__name__)


class WebsiteIA(http.Controller):

    ## HELPER METHODS ##

    def _check_bad_cases(self, cr, uid, request, ia_obj, ia, user_input_obj, context=None):
        # In case of bad ia, redirect to ias list
        if ia_obj.exists(cr, SUPERUSER_ID, ia.id, context=context) == []:
            return werkzeug.utils.redirect("/ia/")

        # In case of auth required, block public user
        if ia.auth_required and uid == request.website.user_id.id:
            return request.website.render("ia.auth_required", {'ia': ia})

        # In case of non open ias
        if ia.stage_id.closed:
            return request.website.render("ia.notopen")

        # If there is no pages
        if not ia.page_ids:
            return request.website.render("ia.nopages")

        # Everything seems to be ok
        return None

    def _check_deadline(self, cr, uid, user_input, context=None):
        '''Prevent opening of the ia if the deadline has turned out

        ! This will NOT disallow access to users who have already partially filled the ia !'''
        if user_input.deadline:
            dt_deadline = datetime.strptime(user_input.deadline, DTF)
            dt_now = datetime.now()
            if dt_now > dt_deadline:  # ia is not open anymore
                return request.website.render("ia.notopen")

        return None

    ## ROUTES HANDLERS ##

    # ia start
    @http.route(['/ia/start/<model("ia.ia"):ia>',
                 '/ia/start/<model("ia.ia"):ia>/<string:token>'],
                type='http', auth='public', website=True)
    def start_ia(self, ia, token=None, **post):
        cr, uid, context = request.cr, request.uid, request.context
        ia_obj = request.registry['ia.ia']
        user_input_obj = request.registry['ia.user_input']

        # Test mode
        if token and token == "phantom":
            _logger.info("[ia] Phantom mode")
            user_input_id = user_input_obj.create(cr, uid, {'ia_id': ia.id, 'test_entry': True}, context=context)
            user_input = user_input_obj.browse(cr, uid, [user_input_id], context=context)[0]
            data = {'ia': ia, 'page': None, 'token': user_input.token}
            return request.website.render('ia.ia_init', data)
        # END Test mode

        # Controls if the ia can be displayed
        errpage = self._check_bad_cases(cr, uid, request, ia_obj, ia, user_input_obj, context=context)
        if errpage:
            return errpage

        # Manual iaing
        if not token:
            vals = {'ia_id': ia.id}
            if request.website.user_id.id != uid:
                vals['partner_id'] = request.registry['res.users'].browse(cr, uid, uid, context=context).partner_id.id
            user_input_id = user_input_obj.create(cr, uid, vals, context=context)
            user_input = user_input_obj.browse(cr, uid, [user_input_id], context=context)[0]
        else:
            try:
                user_input_id = user_input_obj.search(cr, uid, [('token', '=', token)], context=context)[0]
            except IndexError:  # Invalid token
                return request.website.render("website.403")
            else:
                user_input = user_input_obj.browse(cr, uid, [user_input_id], context=context)[0]

        # Do not open expired ia
        errpage = self._check_deadline(cr, uid, user_input, context=context)
        if errpage:
            return errpage

        # Select the right page
        if user_input.state == 'new':  # Intro page
            data = {'ia': ia, 'page': None, 'token': user_input.token}
            return request.website.render('ia.ia_init', data)
        else:
            return request.redirect('/ia/fill/%s/%s' % (ia.id, user_input.token))

    # ia displaying
    @http.route(['/ia/fill/<model("ia.ia"):ia>/<string:token>',
                 '/ia/fill/<model("ia.ia"):ia>/<string:token>/<string:prev>'],
                type='http', auth='public', website=True)
    def fill_ia(self, ia, token, prev=None, **post):
        '''Display and validates a ia'''
        cr, uid, context = request.cr, request.uid, request.context
        ia_obj = request.registry['ia.ia']
        user_input_obj = request.registry['ia.user_input']

        # Controls if the ia can be displayed
        errpage = self._check_bad_cases(cr, uid, request, ia_obj, ia, user_input_obj, context=context)
        if errpage:
            return errpage

        # Load the user_input
        try:
            user_input_id = user_input_obj.search(cr, uid, [('token', '=', token)])[0]
        except IndexError:  # Invalid token
            return request.website.render("website.403")
        else:
            user_input = user_input_obj.browse(cr, uid, [user_input_id], context=context)[0]

        # Do not display expired ia (even if some pages have already been
        # displayed -- There's a time for everything!)
        errpage = self._check_deadline(cr, uid, user_input, context=context)
        if errpage:
            return errpage

        # Select the right page
        if user_input.state == 'new':  # First page
            page, page_nr, last = ia_obj.next_page(cr, uid, user_input, 0, go_back=False, context=context)
            data = {'ia': ia, 'page': page, 'page_nr': page_nr, 'token': user_input.token}
            if last:
                data.update({'last': True})
            return request.website.render('ia.ia', data)
        elif user_input.state == 'done':  # Display success message
            return request.website.render('ia.sfinished', {'ia': ia,
                                                               'token': token,
                                                               'user_input': user_input})
        elif user_input.state == 'skip':
            flag = (True if prev and prev == 'prev' else False)
            page, page_nr, last = ia_obj.next_page(cr, uid, user_input, user_input.last_displayed_page_id.id, go_back=flag, context=context)
            data = {'ia': ia, 'page': page, 'page_nr': page_nr, 'token': user_input.token}
            if last:
                data.update({'last': True})
            return request.website.render('ia.ia', data)
        else:
            return request.website.render("website.403")

    # AJAX prefilling of a ia
    @http.route(['/ia/prefill/<model("ia.ia"):ia>/<string:token>',
                 '/ia/prefill/<model("ia.ia"):ia>/<string:token>/<model("ia.page"):page>'],
                type='http', auth='public', website=True)
    def prefill(self, ia, token, page=None, **post):
        cr, uid, context = request.cr, request.uid, request.context
        user_input_line_obj = request.registry['ia.user_input_line']
        ret = {}

        # Fetch previous answers
        if page:
            ids = user_input_line_obj.search(cr, uid, [('user_input_id.token', '=', token), ('page_id', '=', page.id)], context=context)
        else:
            ids = user_input_line_obj.search(cr, uid, [('user_input_id.token', '=', token)], context=context)
        previous_answers = user_input_line_obj.browse(cr, uid, ids, context=context)

        # Return non empty answers in a JSON compatible format
        for answer in previous_answers:
            if not answer.skipped:
                answer_tag = '%s_%s_%s' % (answer.ia_id.id, answer.page_id.id, answer.question_id.id)
                answer_value = None
                if answer.answer_type == 'free_text':
                    answer_value = answer.value_free_text
                elif answer.answer_type == 'text' and answer.question_id.type == 'textbox':
                    answer_value = answer.value_text
                elif answer.answer_type == 'text' and answer.question_id.type != 'textbox':
                    # here come comment answers for matrices, simple choice and multiple choice
                    answer_tag = "%s_%s" % (answer_tag, 'comment')
                    answer_value = answer.value_text
                elif answer.answer_type == 'number':
                    answer_value = answer.value_number.__str__()
                elif answer.answer_type == 'date':
                    answer_value = answer.value_date
                elif answer.answer_type == 'suggestion' and not answer.value_suggested_row:
                    answer_value = answer.value_suggested.id
                elif answer.answer_type == 'suggestion' and answer.value_suggested_row:
                    answer_tag = "%s_%s" % (answer_tag, answer.value_suggested_row.id)
                    answer_value = answer.value_suggested.id
                if answer_value:
                    dict_soft_update(ret, answer_tag, answer_value)
                else:
                    _logger.warning("[ia] No answer has been found for question %s marked as non skipped" % answer_tag)
        return json.dumps(ret)

    # AJAX scores loading for quiz correction mode
    @http.route(['/ia/scores/<model("ia.ia"):ia>/<string:token>'],
                type='http', auth='public', website=True)
    def get_scores(self, ia, token, page=None, **post):
        cr, uid, context = request.cr, request.uid, request.context
        user_input_line_obj = request.registry['ia.user_input_line']
        ret = {}

        # Fetch answers
        ids = user_input_line_obj.search(cr, uid, [('user_input_id.token', '=', token)], context=context)
        previous_answers = user_input_line_obj.browse(cr, uid, ids, context=context)

        # Compute score for each question
        for answer in previous_answers:
            tmp_score = ret.get(answer.question_id.id, 0.0)
            ret.update({answer.question_id.id: tmp_score + answer.quizz_mark})
        return json.dumps(ret)

    # AJAX submission of a page
    @http.route(['/ia/submit/<model("ia.ia"):ia>'],
                type='http', methods=['POST'], auth='public', website=True)
    def submit(self, ia, **post):
        _logger.debug('Incoming data: %s', post)
        page_id = int(post['page_id'])
        cr, uid, context = request.cr, request.uid, request.context
        ia_obj = request.registry['ia.ia']
        questions_obj = request.registry['ia.question']
        questions_ids = questions_obj.search(cr, uid, [('page_id', '=', page_id)], context=context)
        questions = questions_obj.browse(cr, uid, questions_ids, context=context)

        # Answer validation
        errors = {}
        for question in questions:
            answer_tag = "%s_%s_%s" % (ia.id, page_id, question.id)
            errors.update(questions_obj.validate_question(cr, uid, question, post, answer_tag, context=context))

        ret = {}
        if (len(errors) != 0):
            # Return errors messages to webpage
            ret['errors'] = errors
        else:
            # Store answers into database
            user_input_obj = request.registry['ia.user_input']

            user_input_line_obj = request.registry['ia.user_input_line']
            try:
                user_input_id = user_input_obj.search(cr, uid, [('token', '=', post['token'])], context=context)[0]
            except KeyError:  # Invalid token
                return request.website.render("website.403")
            for question in questions:
                answer_tag = "%s_%s_%s" % (ia.id, page_id, question.id)
                user_input_line_obj.save_lines(cr, uid, user_input_id, question, post, answer_tag, context=context)

            user_input = user_input_obj.browse(cr, uid, user_input_id, context=context)
            go_back = post['button_submit'] == 'previous'
            next_page, _, last = ia_obj.next_page(cr, uid, user_input, page_id, go_back=go_back, context=context)
            vals = {'last_displayed_page_id': page_id}
            if next_page is None and not go_back:
                vals.update({'state': 'done'})
            else:
                vals.update({'state': 'skip'})
            user_input_obj.write(cr, uid, user_input_id, vals, context=context)
            ret['redirect'] = '/ia/fill/%s/%s' % (ia.id, post['token'])
            if go_back:
                ret['redirect'] += '/prev'
        return json.dumps(ret)

    # Printing routes
    @http.route(['/ia/print/<model("ia.ia"):ia>',
                 '/ia/print/<model("ia.ia"):ia>/<string:token>'],
                type='http', auth='public', website=True)
    def print_ia(self, ia, token=None, **post):
        '''Display an ia in printable view; if <token> is set, it will
        grab the answers of the user_input_id that has <token>.'''
        return request.website.render('ia.ia_print',
                                      {'ia': ia,
                                       'token': token,
                                       'page_nr': 0,
                                       'quizz_correction': True if ia.quizz_mode and token else False})

    @http.route(['/ia/results/<model("ia.ia"):ia>'],
                type='http', auth='user', website=True)
    def ia_reporting(self, ia, token=None, **post):
        '''Display ia Results & Statistics for given ia.'''
        result_template ='ia.result'
        current_filters = []
        filter_display_data = []
        filter_finish = False

        ia_obj = request.registry['ia.ia']
        if not ia.user_input_ids or not [input_id.id for input_id in ia.user_input_ids if input_id.state != 'new']:
            result_template = 'ia.no_result'
        if 'finished' in post:
            post.pop('finished')
            filter_finish = True
        if post or filter_finish:
            filter_data = self.get_filter_data(post)
            current_filters = ia_obj.filter_input_ids(request.cr, request.uid, ia, filter_data, filter_finish, context=request.context)
            filter_display_data = ia_obj.get_filter_display_data(request.cr, request.uid, filter_data, context=request.context)
        return request.website.render(result_template,
                                      {'ia': ia,
                                       'ia_dict': self.prepare_result_dict(ia, current_filters),
                                       'page_range': self.page_range,
                                       'current_filters': current_filters,
                                       'filter_display_data': filter_display_data,
                                       'filter_finish': filter_finish
                                       })
        # Quick retroengineering of what is injected into the template for now:
        # (TODO: flatten and simplify this)
        #
        #     ia: a browse record of the ia
        #     ia_dict: very messy dict containing all the info to display answers
        #         {'page_ids': [
        #
        #             ...
        #
        #                 {'page': browse record of the page,
        #                  'question_ids': [
        #
        #                     ...
        #
        #                     {'graph_data': data to be displayed on the graph
        #                      'input_summary': number of answered, skipped...
        #                      'prepare_result': {
        #                                         answers displayed in the tables
        #                                         }
        #                      'question': browse record of the question_ids
        #                     }
        #
        #                     ...
        #
        #                     ]
        #                 }
        #
        #             ...
        #
        #             ]
        #         }
        #
        #     page_range: pager helper function
        #     current_filters: a list of ids
        #     filter_display_data: [{'labels': ['a', 'b'], question_text} ...  ]
        #     filter_finish: boolean => only finished ias or not
        #

    @http.route(['/ia/compare/<model("ia.ia"):ia1>/<string:token1>/vs/<model("ia.ia"):ia2>/<string:token2>'],
                type='http', auth='user', website=True)
    def ia_compare(self, ia1, ia2, token1=None, token2=None, **post):
        return request.website.render('ia.ia_compare',
                                      {'ia_left': ia1,
                                       'ia_right': ia2,
                                       'token_left': token1,
                                       'token_right': token2,
                                       'page_nr': 0,
                                       'quizz_correction': False})

    def prepare_result_dict(self,ia, current_filters=None):
        """Returns dictionary having values for rendering template"""
        current_filters = current_filters if current_filters else []
        ia_obj = request.registry['ia.ia']
        result = {'page_ids': []}
        for page in ia.page_ids:
            page_dict = {'page': page, 'question_ids': []}
            for question in page.question_ids:
                question_dict = {'question':question, 'input_summary':ia_obj.get_input_summary(request.cr, request.uid, question, current_filters, context=request.context), 'prepare_result':ia_obj.prepare_result(request.cr, request.uid, question, current_filters, context=request.context), 'graph_data': self.get_graph_data(question, current_filters)}
                page_dict['question_ids'].append(question_dict)
            result['page_ids'].append(page_dict)
        return result

    def get_filter_data(self, post):
        """Returns data used for filtering the result"""
        filters = []
        for ids in post:
            #if user add some random data in query URI, ignore it
            try:
                row_id, answer_id = ids.split(',')
                filters.append({'row_id': int(row_id), 'answer_id': int(answer_id)})
            except:
                return filters
        return filters

    def page_range(self, total_record, limit):
        '''Returns number of pages required for pagination'''
        total = ceil(total_record / float(limit))
        return range(1, int(total + 1))

    def get_graph_data(self, question, current_filters=None):
        '''Returns formatted data required by graph library on basis of filter'''
        # TODO refactor this terrible method and merge it with prepare_result_dict
        current_filters = current_filters if current_filters else []
        ia_obj = request.registry['ia.ia']
        result = []
        if question.type == 'multiple_choice':
            result.append({'key': str(question.question),
                           'values': ia_obj.prepare_result(request.cr, request.uid, question, current_filters, context=request.context)['answers']
                           })
        if question.type == 'simple_choice':
            result = ia_obj.prepare_result(request.cr, request.uid, question, current_filters, context=request.context)['answers']
        if question.type == 'matrix':
            data = ia_obj.prepare_result(request.cr, request.uid, question, current_filters, context=request.context)
            for answer in data['answers']:
                values = []
                for row in data['rows']:
                    values.append({'text': data['rows'].get(row), 'count': data['result'].get((row, answer))})
                result.append({'key': data['answers'].get(answer), 'values': values})
        return json.dumps(result)

def dict_soft_update(dictionary, key, value):
    ''' Insert the pair <key>: <value> into the <dictionary>. If <key> is
    already present, this function will append <value> to the list of
    existing data (instead of erasing it) '''
    if key in dictionary:
        dictionary[key].append(value)
    else:
        dictionary.update({key: [value]})
