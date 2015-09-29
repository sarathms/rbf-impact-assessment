from openerp.osv import fields, osv
from openerp import tools

class ia_report(osv.osv):
    _name = "ia.report"
    _description = "Impact Assessment Analysis"
    _auto = False

    _columns = {
        'id': fields.many2one('ia.user_input_line', 'Answer', readonly=True),
        'ia_id': fields.many2one('ia.ia', 'Impact Assessment', readonly=True),
        'input_id': fields.many2one('ia.user_input', 'User Input', readonly=True),
        'submission_date': fields.datetime('Date of Submission', readonly=True),
        'partner_id': fields.many2one('res.partner', 'Submitter', readonly=True),
        'question_id': fields.many2one('ia.question', 'Question', readonly=True),
        'value': fields.char('Answer', readonly=True),
        'submissions': fields.integer('# of submissions', readonly=True)
    }

    def _select(self):
        select_str = """
            iline.id as id,
            iline.ia_id as ia_id,
            iline.user_input_id as input_id,
            iline.write_date as submission_date,
            input.partner_id as partner_id,
            q.id as question_id,
            COALESCE (iline.value_text, CAST(iline.value_suggested as text)) as value,
            1 as submissions
        """
        return select_str

    def _from(self):
        from_str = """
                ia_user_input_line iline
                    left join ia_question q on (q.id=iline.question_id)
                    left join ia_user_input input on (input.id=iline.user_input_id)
        """
        return from_str

    def _where(self):
        where_str = """
                input.partner_id IS NOT NULL
        """
        return where_str

    def _group_by(self):
        group_by_str = """
                iline.ia_id,
                iline.user_input_id,
                iline.write_date,
                input.partner_id,
                q.id,
                iline.id
        """
        return group_by_str

    def init(self, cr):
        self._table = 'ia_report'
        tools.drop_view_if_exists(cr, self._table)
        cr.execute("""CREATE or REPLACE VIEW %s as (
            SELECT %s
            FROM ( %s )
            WHERE ( %s )
            GROUP BY %s
            )""" % (self._table, self._select(), self._from(), self._where(), self._group_by()))

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
