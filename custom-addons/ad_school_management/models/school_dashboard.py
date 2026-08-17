from odoo import models, fields, api, _

class SchoolDashboard(models.TransientModel):
    _name = 'school.dashboard'
    _description = 'School Dashboard KPIs'

    name = fields.Char(string='Title', default='School KPIs Dashboard')

    @api.model
    def action_open_dashboard(self):
        return {
            'type': 'ir.actions.client',
            'tag': 'school_dashboard',
            'name': _('Dashboard'),
            'target': 'current',
        }

    @api.model
    def get_dashboard_stats(self):
        today = fields.Date.context_today(self)
        
        total_students = self.env['school.student'].search_count([])
        enrolled_students = self.env['school.student'].search_count([('student_status', '=', 'enrolled')])
        draft_students = self.env['school.student'].search_count([('student_status', '=', 'draft')])
        promoted_students = self.env['school.student'].search_count([('student_status', '=', 'promoted')])
        
        total_teachers = self.env['school.teacher'].search_count([])
        total_parents = self.env['school.parent'].search_count([])
        
        total_admissions = self.env['school.admission'].search_count([])
        pending_admissions = self.env['school.admission'].search_count([('state', '=', 'submitted')])
        approved_admissions = self.env['school.admission'].search_count([('state', '=', 'approved')])
        
        fees = self.env['school.student.fee'].search([])
        invoiced_fees = sum(fees.filtered(lambda f: f.state == 'invoiced').mapped('net_amount'))
        paid_fees = sum(fees.filtered(lambda f: f.state == 'paid').mapped('net_amount'))
        total_outstanding = invoiced_fees
        
        total_marked_today = self.env['school.attendance'].search_count([('date', '=', today)])
        present_today = self.env['school.attendance'].search_count([
            ('date', '=', today),
            ('status', 'in', ('present', 'late'))
        ])
        attendance_rate = round((present_today / total_marked_today) * 100, 1) if total_marked_today > 0 else 100.0

        return {
            'students': {
                'total': total_students,
                'enrolled': enrolled_students,
                'draft': draft_students,
                'promoted': promoted_students,
            },
            'faculty_parents': {
                'teachers': total_teachers,
                'parents': total_parents,
            },
            'admissions': {
                'total': total_admissions,
                'pending': pending_admissions,
                'approved': approved_admissions,
            },
            'finance': {
                'paid': paid_fees,
                'outstanding': total_outstanding,
                'total': paid_fees + total_outstanding,
                'collection_rate': round((paid_fees / (paid_fees + total_outstanding)) * 100, 1) if (paid_fees + total_outstanding) > 0 else 0.0,
            },
            'attendance': {
                'marked': total_marked_today,
                'present': present_today,
                'rate': attendance_rate,
            }
        }
