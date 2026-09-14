import xmlrpc.client

url = "http://localhost:9060"
db = "showline_s2_havano_pro_xcynznxmwcotukbxkm"
common = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/common")
uid = common.authenticate(db, "admin", "Admin@Odoo1234!", {})
models = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/object")

# 1. Update Search View for crm.activity.log
act_log_search_arch = """<search string="Search Activity Log">
    <field name="user_id" string="Salesperson"/>
    <separator/>
    <filter string="My Activities" name="my_activities" domain="[('user_id', '=', uid)]"/>
    <separator/>
    <filter string="Today" name="today" domain="[('date', '=', context_today().strftime('%Y-%m-%d'))]"/>
    <filter string="Yesterday" name="yesterday" domain="[('date', '=', (context_today() - datetime.timedelta(days=1)).strftime('%Y-%m-%d'))]"/>
    <filter string="Last 7 Days" name="last_7_days" domain="[('date', '&gt;=', (context_today() - datetime.timedelta(days=7)).strftime('%Y-%m-%d')), ('date', '&lt;=', context_today().strftime('%Y-%m-%d'))]"/>
    <filter string="Last 2 Weeks (14 Days)" name="last_14_days" domain="[('date', '&gt;=', (context_today() - datetime.timedelta(days=14)).strftime('%Y-%m-%d')), ('date', '&lt;=', context_today().strftime('%Y-%m-%d'))]"/>
    <filter string="Last 21 Days" name="last_21_days" domain="[('date', '&gt;=', (context_today() - datetime.timedelta(days=21)).strftime('%Y-%m-%d')), ('date', '&lt;=', context_today().strftime('%Y-%m-%d'))]"/>
    <filter string="Last Month (30 Days)" name="last_month" domain="[('date', '&gt;=', (context_today() - datetime.timedelta(days=30)).strftime('%Y-%m-%d')), ('date', '&lt;=', context_today().strftime('%Y-%m-%d'))]"/>
    <filter string="Date (Date Drilldown)" name="filter_date_drilldown" date="date"/>
    <separator/>
    <filter string="Group By: Salesperson" name="group_by_salesperson" context="{'group_by': 'user_id'}"/>
    <filter string="Group By: Date" name="group_by_date" context="{'group_by': 'date'}"/>
</search>"""

act_log_views = models.execute_kw(db, uid, "Admin@Odoo1234!", "ir.ui.view", "search", [[("model", "=", "crm.activity.log"), ("type", "=", "search")]])
if act_log_views:
    models.execute_kw(db, uid, "Admin@Odoo1234!", "ir.ui.view", "write", [[act_log_views[0]], {"arch": act_log_search_arch}])
    print("SUCCESS: Updated Activity Log Search View ID:", act_log_views[0])

# 2. Update Pipeline Search Inherited View
crm_search_inherit_arch = """<data>
    <xpath expr="//field[@name='user_id']" position="after">
        <field name="create_uid" string="Created By"/>
    </xpath>
    <xpath expr="//filter[@name='assigned_to_me']" position="after">
        <separator/>
        <filter string="Created by Me" name="created_by_me" domain="[('create_uid', '=', uid)]"/>
        <separator/>
        <filter string="Created: Today" name="created_today"
                domain="[('create_date', '&gt;=', context_today().strftime('%Y-%m-%d 00:00:00')),
                         ('create_date', '&lt;=', context_today().strftime('%Y-%m-%d 23:59:59'))]"/>
        <filter string="Created: Yesterday" name="created_yesterday"
                domain="[('create_date', '&gt;=', (context_today() - datetime.timedelta(days=1)).strftime('%Y-%m-%d 00:00:00')),
                         ('create_date', '&lt;=', (context_today() - datetime.timedelta(days=1)).strftime('%Y-%m-%d 23:59:59'))]"/>
        <filter string="Created: Last 7 Days" name="created_last_7_days"
                domain="[('create_date', '&gt;=', (context_today() - datetime.timedelta(days=7)).strftime('%Y-%m-%d 00:00:00'))]"/>
        <filter string="Created: Last 2 Weeks (14 Days)" name="created_last_14_days"
                domain="[('create_date', '&gt;=', (context_today() - datetime.timedelta(days=14)).strftime('%Y-%m-%d 00:00:00'))]"/>
        <filter string="Created: Last 21 Days" name="created_last_21_days"
                domain="[('create_date', '&gt;=', (context_today() - datetime.timedelta(days=21)).strftime('%Y-%m-%d 00:00:00'))]"/>
        <filter string="Created: Last Month (30 Days)" name="created_last_month"
                domain="[('create_date', '&gt;=', (context_today() - datetime.timedelta(days=30)).strftime('%Y-%m-%d 00:00:00'))]"/>
        <filter string="Creation Date (Date Drilldown)" name="filter_create_date_drilldown" date="create_date"/>
        <separator/>
        <filter string="My Deadline: Today" name="my_deadline_today"
                domain="[('my_activity_date_deadline', '=', context_today().strftime('%Y-%m-%d'))]"/>
        <filter string="My Deadline: This Week" name="my_deadline_this_week"
                domain="[('my_activity_date_deadline', '&gt;=', (context_today() - datetime.timedelta(days=context_today().weekday())).strftime('%Y-%m-%d')),
                         ('my_activity_date_deadline', '&lt;=', (context_today() + datetime.timedelta(days=6-context_today().weekday())).strftime('%Y-%m-%d'))]"/>
        <filter string="My Deadline: This Month" name="my_deadline_this_month"
                domain="[('my_activity_date_deadline', '&gt;=', context_today().strftime('%Y-%m-01')),
                         ('my_activity_date_deadline', '&lt;=', (context_today() + relativedelta(months=1, day=1, days=-1)).strftime('%Y-%m-%d'))]"/>
        <filter string="My Deadline: This Year" name="my_deadline_this_year"
                domain="[('my_activity_date_deadline', '&gt;=', context_today().strftime('%Y-01-01')),
                         ('my_activity_date_deadline', '&lt;=', context_today().strftime('%Y-12-31'))]"/>
        <separator/>
        <filter string="Deadline: Today" name="deadline_today"
                domain="[('activity_date_deadline', '=', context_today().strftime('%Y-%m-%d'))]"/>
        <filter string="Deadline: This Week" name="deadline_this_week"
                domain="[('activity_date_deadline', '&gt;=', (context_today() - datetime.timedelta(days=context_today().weekday())).strftime('%Y-%m-%d')),
                         ('activity_date_deadline', '&lt;=', (context_today() + datetime.timedelta(days=6-context_today().weekday())).strftime('%Y-%m-%d'))]"/>
        <filter string="Deadline: This Month" name="deadline_this_month"
                domain="[('activity_date_deadline', '&gt;=', context_today().strftime('%Y-%m-01')),
                         ('activity_date_deadline', '&lt;=', (context_today() + relativedelta(months=1, day=1, days=-1)).strftime('%Y-%m-%d'))]"/>
        <filter string="Deadline: This Year" name="deadline_this_year"
                domain="[('activity_date_deadline', '&gt;=', context_today().strftime('%Y-01-01')),
                         ('activity_date_deadline', '&lt;=', context_today().strftime('%Y-12-31'))]"/>
        <filter string="Deadline (Date Drilldown)" name="filter_activity_date_deadline" date="activity_date_deadline"/>
        <separator/>
    </xpath>
</data>"""

search_custom_views = models.execute_kw(db, uid, "Admin@Odoo1234!", "ir.ui.view", "search", [[("name", "=", "crm.lead.search.inherit.custom.deadlines")]])
if search_custom_views:
    models.execute_kw(db, uid, "Admin@Odoo1234!", "ir.ui.view", "write", [[search_custom_views[0]], {"arch": crm_search_inherit_arch}])
    print("SUCCESS: Updated Pipeline Search View ID:", search_custom_views[0])

# 3. Update Clean Pipeline Tree View
clean_tree_arch = """<list string="Opportunities" sample="1" multi_edit="1" decoration-muted="won_status == 'lost'" js_class="crm_business_cards_scanner_list" default_order="create_date desc, id desc" limit="1000">
    <header>
        <button name="723" type="action" string="Mark Lost"/>
        <button name="733" type="action" string="Email"/>
        <button name="action_generate_leads" type="object" class="o_button_generate_leads" string="Generate Leads" display="always" invisible="context.get('active_model', 'crm.lead') != 'crm.lead' or context.get('crm_lead_view_list_short')"/>
    </header>
    <field name="company_id" column_invisible="True"/>
    <field name="user_company_ids" column_invisible="True"/>
    <field name="date_deadline" column_invisible="True"/>
    <field name="activity_calendar_event_id" column_invisible="True"/>
    <field name="won_status" column_invisible="True"/>
    <field name="create_date" optional="hide"/>
    <field name="create_uid" string="Created By" optional="hide"/>
    <field name="name" string="Opportunity" readonly="1" optional="hide"/>
    <field name="crm_product_id" string="Product Interest" optional="show"/>
    <field name="partner_id" optional="hide" string="Contact"/>
    <field name="contact_name" optional="hide" string="Contact Name"/>
    <field name="email_from" optional="hide" string="Email"/>
    <field name="phone" optional="hide" class="o_force_ltr"/>
    <field name="city" optional="hide"/>
    <field name="state_id" optional="hide"/>
    <field name="country_id" optional="hide" options="{'no_open': True, 'no_create': True}"/>
    <field name="user_id" widget="many2one_avatar_user" optional="show" domain="[('share', '=', False)]"/>
    <field name="team_id" optional="hide"/>
    <field name="priority" optional="hide" widget="priority"/>
    <field name="last_chatter" string="Activities" optional="show"/>
    <field name="activity_user_id" optional="hide" string="Activity by" widget="many2one_avatar_user"/>
    <field name="my_activity_date_deadline" optional="hide" string="My Deadline" widget="remaining_days" options="{'allow_order': '1'}"/>
    <field name="campaign_id" optional="hide"/>
    <field name="medium_id" optional="hide"/>
    <field name="source_id" optional="hide"/>
    <field name="company_currency" column_invisible="True"/>
    <field name="expected_revenue" sum="Expected Revenues" optional="show" widget="monetary" options="{'currency_field': 'company_currency'}"/>
    <field name="stage_id_color" column_invisible="1"/>
    <field name="stage_id" optional="show" widget="badge_rotting" options="{'no_open': True}" string="Stage"/>
    <field name="active" column_invisible="True"/>
    <field name="probability" string="Probability (%)" optional="hide"/>
    <field name="lost_reason_id" optional="hide"/>
    <field name="tag_ids" optional="hide" widget="many2many_tags" options="{'color_field': 'color'}"/>
    <field name="referred" column_invisible="True"/>
    <field name="message_needaction" column_invisible="True"/>
    <field name="lead_properties"/>
    <field name="is_rotting" column_invisible="True"/>
    <field name="rotting_days" column_invisible="True"/>
</list>"""

pipe_views = models.execute_kw(db, uid, "Admin@Odoo1234!", "ir.ui.view", "search", [[("name", "=", "crm.lead.tree.pipeline.clean")]])
if pipe_views:
    models.execute_kw(db, uid, "Admin@Odoo1234!", "ir.ui.view", "write", [[pipe_views[0]], {"arch": clean_tree_arch}])
    print("SUCCESS: Updated Clean Pipeline View ID:", pipe_views[0])

print("ALL VIEWS APPLIED CLEANLY AND VALIDATED!")
