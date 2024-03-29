/*
* model: partnerOrganizationModel
*
* Defines model for individual sector.
*/
define([
  'jquery',
  'underscore',
  'backbone'
], function($, _, Backbone){
  var partnerOrganizationModel = Backbone.Model.extend({
    urlRoot: '/partners/partner',
    defaults: {
      partner_id: null,
      name: null, 
      description: null,
      email: null,
      contact_person: null,
      phone_number: null
    }
  });
  return partnerOrganizationModel;
});
