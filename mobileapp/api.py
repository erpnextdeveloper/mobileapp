from __future__ import unicode_literals
import frappe
from frappe.utils import cint, get_gravatar, format_datetime, now_datetime,add_days,today,formatdate,date_diff,getdate,get_last_day,flt,nowdate
from frappe import throw, msgprint, _
from frappe.utils.password import update_password as _update_password
from frappe.desk.notifications import clear_notifications
from frappe.utils.user import get_system_managers
import frappe.permissions
import frappe.share
from frappe.model.mapper import get_mapped_doc
import re
import string
import random
import json
import time
from six import string_types
from frappe.desk.form.save import cancel
from frappe.desk.form.linked_with import get_linked_docs
from frappe.contacts.doctype.address.address import get_company_address
from frappe.model.utils import get_fetch_values
from datetime import datetime
from datetime import date
from datetime import timedelta
import collections
import math
from frappe.core.doctype.sms_settings.sms_settings import send_via_gateway,validate_receiver_nos
import traceback
from frappe.contacts.doctype.address.address import get_address_display
from erpnext.crm.doctype.lead.lead import make_customer
from frappe.desk import query_report

@frappe.whitelist()
def appErrorLog(title,error):
	d = frappe.get_doc({
			"doctype": "App Error Log",
			"title":str("User:")+str(title+" "+"Website Error"),
			"error":traceback.format_exc()
		})
	d = d.insert(ignore_permissions=True)
	return d

@frappe.whitelist()
def generateResponse(_type,status=None,message=None,data=None,error=None):
	response= {}
	if _type=="S":
		if status:
			response["status"]=int(status)
		else:
			response["status"]=200
		response["message"]=message
		response["data"]=data
	else:
		error_log=appErrorLog(frappe.session.user,str(error))
		if status:
			response["status"]=status
		else:
			response["status"]=500
		if message:
			response["message"]=message
		else:
			response["message"]="Something Went Wrong"		
		response["message"]=message
		response["data"]=None
	return response



@frappe.whitelist()
def addLead(lead_name,gender,source,email_id,mobile_no,salutation=None):
	try:
		lead_data=frappe.get_all("Lead",filters={"email_id":email_id},fields=["name"])
		if lead_data:
			return generateResponse("S","409",message="Duplicate Email Id For Lead",data=[])
		lead=frappe.get_doc(dict(
			doctype="Lead",
			lead_name=lead_name,
			gender=gender,
			source=source,
			email_id=email_id,
			lead_owner=frappe.session.user,
			salutation=salutation if not salutation==None else '',
			mobile_no=mobile_no
		)).insert(ignore_permissions=True)
		return generateResponse("S",message="Insert Successfully",data=lead)

	except Exception as e:
		return generateResponse("F",error=e)


@frappe.whitelist(allow_guest=True)
def makeCustomer(first_name,address_type,address_line1,city,pincode,state,country,last_name=None,address_line2=None,phone=None,warehouse=None,customer_group=None,territory=None,popularity_rating=None,reputation_score=None,credit_limit=None,payment_terms=None,established_date=None,staff=None,market_segment=None,industry=None):
	try:
		customer_name=''
		if not last_name==None:
			customer_name=first_name+' '+last_name
		else:
			customer_name=first_name

		customer=frappe.get_doc(dict(
			doctype="Customer",
			customer_name=customer_name
		)).insert(ignore_permissions=True)
		makeAddress(customer.name,address_type,address_line1,city,pincode,state,country,address_line2=None,phone=None)
		return generateResponse("S",message="Insert Successfully",data=customer)

	except Exception as e:
		return generateResponse("F",error=e)

@frappe.whitelist(allow_guest=True)
def makeAddress(customer,address_type,address_line1,city,pincode,state,latitude=None,longitude=None,country=None,address_line2=None,phone=None,gstin=None,address_title=None,gst_state=None,visibility=None,area=None,floor=None,ownership=None,inside_image=None,outside_image=None,remarks=None):
	try:
		billing=0
		shipping=0
		if address_type=="Billing":
			billing=1
		if address_type=="Shipping":
			shipping=1
		if address_type=="Both":
			billing=1
			shipping=1
		json_obj='{"type":"FeatureCollection","features":[{"type":"Feature","properties":{"point_type":"circle","radius":100},"geometry":{"type":"Point","coordinates":['+longitude+','+latitude+']}}]}'
		link=[]
		link_json={}
		link_json["parentfield"]="links"
		link_json["parenttype"]="Address"
		link_json["link_doctype"]="Customer"
		link_json["link_name"]=str(customer)
		link.append(link_json)
		address_doc=frappe.get_doc(dict(
				doctype="Address",
				address_type='Billing',
				is_primary_address=billing,
				is_shipping_address=shipping,
				address_line1=address_line1,
				address_line2=address_line2,
				city=city,
				pincode=pincode,
				state=state,
				phone=phone,
				gstin=gstin,
				links=link,
				country=country,
				geolocation=json_obj
				)).insert(ignore_permissions=True)
		return generateResponse("S",message="Insert Successfully",data=address_doc)
	except Exception as e:
		return generateResponse("F",error=e)


@frappe.whitelist()
def customerList():
	try:
		customer_list=frappe.get_list("Customer",filters={},fields=["*"])
		return generateResponse("S",message="Customer List Get Successfully",data=customer_list)

	except Exception as e:
		return generateResponse("F",error=e)

@frappe.whitelist()
def makeEvent(subject,event_category,event_type,starts_on,ends_on,customer):
	try:
		ref=[]
		ref_json={}
		ref_json["parentfield"]="event_participants"
		ref_json["parenttype"]="Event"
		ref_json["reference_doctype"]="Customer"
		ref_json["reference_docname"]=customer
		ref.append(ref_json)
		event=frappe.get_doc(dict(
			doctype="Event",
			subject=subject,
			event_category=event_category,
			event_type=event_type,
			starts_on=str(starts_on),
			ends_on=str(ends_on),
			event_participants=ref
		)).insert()
		return generateResponse("S",message="Event Added Successfully",data=event)
	except Exception as e:
		return generateResponse("F",error=e)

@frappe.whitelist()
def getGL(customer,from_date,end_date):
	try:
		filter_json={}	
		filter_json["party_type"] = "Customer"
		filter_json["party"] = str(customer)
		filter_json["from_date"] = str(from_date)
		filter_json["to_date"] = str(end_date) 
		filter_json["group_by"] = "Group by Voucher (Consolidated)"	
		res=query_report.run("Combine General Ledger",filter_json)
		return generateResponse("S",message="Data Get Successfully",data=res["result"])
	except Exception as e:
		return generateResponse("F",error=e)

@frappe.whitelist()
def getVoucherDetails(voucher_type,voucher_no):
	try:
		doc=frappe.get_doc(str(voucher_type),str(voucher_no))
		return generateResponse("S",message="Data Get Successfully",data=doc)
	except Exception as e:
		return generateResponse("F",error=e)


@frappe.whitelist()
def getPendingInvoice(customer,from_date,to_date):
	try:
		invoice_list=frappe.get_list("Sales Invoice",filters=[["Sales Invoice","customer","=",str(customer)],["Sales Invoice","status","not in",["Draft","Paid","Cancelled","Return","Credit Note Issued"]],["Sales Invoice","posting_date","Between",[str(from_date),str(to_date)]]],fields=["posting_date","name","grand_total","rounded_total","outstanding_amount","status"])
		return generateResponse("S",message="Data Get Successfully",data=invoice_list)
		

	except Exception as e:
		return generateResponse("F",error=e)


@frappe.whitelist()
def getItemwiseInventory(item_code):
	try:
		item='%'+item_code+'%'
		#item_list=frappe.db.sql("""select name,brand,item_name from `tabItem` where item_code like %s and disabled=0""",item,as_dict=1)
		#return item_list
		item_list=frappe.get_list("Item",filters=[["Item","item_code","like",str(item)]],fields=["name","brand","item_name"])
		result=[]
		for row in item_list:
			filter_json={}	
			filter_json["item_code"] = str(row.name)
			filter_json["from_date"] = str(today())
			filter_json["to_date"] = str(today()) 
			res=query_report.run("Stock Balance",filter_json)
			for res_row in res["result"]:
				item_json={}
				item_json["item_code"]=res_row[0]
				item_json["item_name"]=res_row[1]
				item_json["brand"]=res_row[3]
				item_json["warehouse"]=res_row[5]
				item_json["qty"]=res_row[13]
				result.append(item_json)
		return generateResponse("S",message="Data Get Successfully",data=result)
	except Exception as e:
		return generateResponse("F",error=e)


@frappe.whitelist()
def getEventDetails(customer=None,number=None,from_date=None,to_date=None):
	try:
		event_doc=[]
		if not customer==None:
			if not number==None:
				event_doc=frappe.db.sql("""select e.name,ep.reference_docname as 'customer',e.event_category as 'category',e.event_type as 'event_type',e.subject,e.description from `tabEvent` as e inner join `tabEvent Participants` as ep where e.name=ep.parent and ep.reference_doctype='Customer' and ep.reference_docname=%s limit %s""",(customer,int(number)),as_dict=1)
			if not from_date==None and not to_date==None:
				event_doc=frappe.db.sql("""select e.name,ep.reference_docname as 'customer',e.event_category as 'category',e.event_type as 'event_type',e.subject,e.description from `tabEvent` as e inner join `tabEvent Participants` as ep where e.name=ep.parent and ep.reference_doctype='Customer' and ep.reference_docname=%s and cast(starts_on AS date) between %s and %s""",(customer,from_date,to_date),as_dict=1)
			
			return generateResponse("S",message="Data Get Successfully",data=event_doc)

		else:
			if not number==None:
				event_doc=frappe.db.sql("""select e.name,ep.reference_docname as 'customer',e.event_category as 'category',e.event_type as 'event_type',e.subject,e.description from `tabEvent` as e inner join `tabEvent Participants` as ep where e.name=ep.parent and ep.reference_doctype='Customer' limit %s""",int(number),as_dict=1)
			if not from_date==None and not to_date==None:
				event_doc=frappe.db.sql("""select e.name,ep.reference_docname as 'customer',e.event_category as 'category',e.event_type as 'event_type',e.subject,e.description from `tabEvent` as e inner join `tabEvent Participants` as ep where e.name=ep.parent and ep.reference_doctype='Customer' and cast(starts_on AS date) between %s and %s""",(from_date,to_date),as_dict=1)
			return generateResponse("S",message="Data Get Successfully",data=event_doc)
	except Exception as e:
		return generateResponse("F",error=e)


@frappe.whitelist()
def makeCustomerFromLead(lead_no):
	try:
		lead_data=make_customer(lead_no)
		res=lead_data.insert()
		return generateResponse("S",message="Lead Converted Successfully",data=res)
	except Exception as e:
		return generateResponse("F",error=e)



@frappe.whitelist()
def makeContact(customer,first_name,mobile_no,email_id,last_name=None,gender=None,departmeny=None,designation=None,birthday=None,anniversary=None):
	try:
		link_dict=[]
		link_json={}
		link_json["link_doctype"]="Customer"
		link_json["link_name"]=customer
		link_dict.append(link_json)
		con_doc=frappe.get_doc(dict(
			doctype="Contact",
			first_name=first_name,
			last_name=last_name,
			mobile_no=mobile_no,
			email_id=email_id,
			links=link_dict
		)).insert()
		return generateResponse("S",message="Insert Successfully",data=con_doc)
		
	except Exception as e:
		return generateResponse("F",error=e)



@frappe.whitelist()
def makeAssociatedProducts(customer,item_group=None,brand=None,remarks=None):
	try:
		doc=frappe.get_doc(dict(
			doctype="Associated Products",
			parent=customer,
			parentfield="associated_products",
			parenttype="Customer",
			item_group=item_group,
			brand=brand,
			remarks=remarks
		)).insert()
		return generateResponse("S",message="Insert Successfully",data=doc)
	except Exception as e:
		return generateResponse("F",error=e)

@frappe.whitelist()
def makeAssociations(customer,associations=None,remarks=None):
	try:
		doc=frappe.get_doc(dict(
			doctype="Associations",
			parent=customer,
			parentfield="associations",
			parenttype="Customer",
			associations=associations,
			remarks=remarks
		)).insert()
		return generateResponse("S",message="Insert Successfully",data=doc)
	except Exception as e:
		return generateResponse("F",error=e)


@frappe.whitelist()
def getDuePayment(customer,paid_amount,date,company,mode_of_payment,reference_no,reference_date):
	try:
		doc=frappe.get_doc(dict(
			doctype="Payment Entry",
			company=company,
			posting_date=date,
			mode_of_payment=mode_of_payment,
			party_type="Customer",
			party=customer,
			paid_amount=flt(paid_amount),
			received_amount=flt(paid_amount),
			reference_no=reference_no,
			reference_date=reference_date,
			payment_type="Receive",
			paid_to="Cash - SI"
		)).insert()
		return doc




	except Exception as e:
		return generateResponse("F",error=e)













	






		
		
	
	


