from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class SchoolStudent(models.Model):
    _name = 'school.student'
    _description = 'Student'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _inherits = {'res.partner': 'partner_id'}
    _order = 'roll_number, name'

    partner_id = fields.Many2one('res.partner', string='Partner', required=True, ondelete='cascade')
    
    admission_no = fields.Char(string='Admission No.', readonly=True, copy=False)
    class_id = fields.Many2one('school.class', string='Class', required=True, tracking=True)
    section_id = fields.Many2one('school.section', string='Section', required=True, tracking=True)
    academic_year_id = fields.Many2one('school.academic.year', string='Academic Year', required=True, tracking=True)
    roll_number = fields.Char(string='Roll Number', tracking=True, copy=False)
    parent_ids = fields.Many2many('school.parent', 'school_student_parent_rel', 'student_id', 'parent_id', string='Parents/Guardians')

    exam_result_ids = fields.One2many('school.exam.result', 'student_id', string='Exam Results')
    gpa = fields.Float(string='GPA', compute='_compute_gpa', store=True)

    student_fee_ids = fields.One2many('school.student.fee', 'student_id', string='Fees')
    fee_count = fields.Integer(string='Fee Count', compute='_compute_fee_count')

    photo = fields.Binary(related='partner_id.image_1920', readonly=False, string='Photo')
 
    _admission_no_uniq = models.Constraint(
        'unique(admission_no)', 'The admission number must be unique!'
    )

    @api.depends('exam_result_ids.gpa')
    def _compute_gpa(self):
        for student in self:
            results = student.exam_result_ids
            if results:
                student.gpa = sum(results.mapped('gpa')) / len(results)
            else:
                student.gpa = 0.0
 
    @api.depends('student_fee_ids')
    def _compute_fee_count(self):
        for student in self:
            student.fee_count = len(student.student_fee_ids)

    def _get_section_students(self, class_id, section_id, academic_year_id, exclude_id=None):
        domain = [
            ('class_id', '=', class_id),
            ('section_id', '=', section_id),
            ('academic_year_id', '=', academic_year_id),
        ]
        if exclude_id:
            domain.append(('id', '!=', exclude_id))
        return self.search(domain)

    def _get_next_roll_number(self, existing_students):
        existing_roll_numbers = [
            int(student.roll_number)
            for student in existing_students
            if student.roll_number and student.roll_number.isdigit()
        ]
        return str(max(existing_roll_numbers) + 1) if existing_roll_numbers else '1'

    @api.onchange('section_id', 'class_id', 'academic_year_id')
    def _onchange_section_id(self):
        if self.section_id and self.class_id and self.academic_year_id:
            exclude_id = self.id if isinstance(self.id, int) else None
            existing_students = self._get_section_students(
                self.class_id.id, self.section_id.id, self.academic_year_id.id, exclude_id
            )

            if len(existing_students) >= self.section_id.capacity:
                self.roll_number = False
                return {
                    'warning': {
                        'title': _('Section Full'),
                        'message': _(
                            "Section %s has already reached its maximum capacity of %s students! "
                            "Please select a different section."
                        ) % (self.section_id.name, self.section_id.capacity),
                    }
                }

            self.roll_number = self._get_next_roll_number(existing_students)
        else:
            self.roll_number = False

    @api.model_create_multi
    def create(self, vals_list):
        next_roll_number_map = {}
        for vals in vals_list:
            if not vals.get('admission_no'):
                vals['admission_no'] = self.env['ir.sequence'].next_by_code('school.student.admission') or '/'
            vals['is_student'] = True

            if 'student_status' not in vals:
                partner_id = vals.get('partner_id')
                if partner_id:
                    partner = self.env['res.partner'].browse(partner_id)
                    vals['student_status'] = partner.student_status or 'draft'
                else:
                    vals['student_status'] = 'draft'

            if vals.get('class_id') and vals.get('section_id') and vals.get('academic_year_id'):
                key = (vals['class_id'], vals['section_id'], vals['academic_year_id'])
                if key not in next_roll_number_map:
                    existing_students = self._get_section_students(*key)
                    next_roll_number_map[key] = int(self._get_next_roll_number(existing_students))
                vals['roll_number'] = str(next_roll_number_map[key])
                next_roll_number_map[key] += 1
        return super(SchoolStudent, self).create(vals_list)

    @api.constrains('roll_number', 'class_id', 'section_id', 'academic_year_id')
    def _check_roll_number(self):
        for student in self:
            if student.roll_number:
                duplicate = self.search([
                    ('id', '!=', student.id),
                    ('roll_number', '=', student.roll_number),
                    ('class_id', '=', student.class_id.id),
                    ('section_id', '=', student.section_id.id),
                    ('academic_year_id', '=', student.academic_year_id.id)
                ])
                if duplicate:
                    raise ValidationError(_(
                        "Roll number %s already exists in class %s, section %s for academic year %s!"
                    ) % (student.roll_number, student.class_id.name, student.section_id.name, student.academic_year_id.name))

    @api.constrains('class_id', 'section_id')
    def _check_section_capacity(self):
        for student in self:
            if student.section_id:
                student_count = self.search_count([
                    ('class_id', '=', student.class_id.id),
                    ('section_id', '=', student.section_id.id),
                    ('academic_year_id', '=', student.academic_year_id.id),
                    ('id', '!=', student.id)
                ])
                if student_count >= student.section_id.capacity:
                    raise ValidationError(_(
                        "Section %s has reached its maximum capacity of %s students!"
                    ) % (student.section_id.name, student.section_id.capacity))

    def action_view_fees(self):
        self.ensure_one()
        action = {
            'name': _('Fees'),
            'type': 'ir.actions.act_window',
            'res_model': 'school.student.fee',
            'domain': [('student_id', '=', self.id)],
            'context': {'default_student_id': self.id},
        }
        if self.fee_count == 1:
            action.update({
                'view_mode': 'form',
                'res_id': self.student_fee_ids[0].id,
            })
        else:
            action['view_mode'] = 'list,form'
        return action
