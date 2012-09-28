Ext.define('metrics_find', {
  extend: 'Ext.data.Model',
  fields: [
      'path',
      'is_leaf'
  ]
});

var store = new Ext.data.Store({
  autoLoad: true,
  model: 'metrics_find',
  fields: ['path', 'is_leaf'],
  proxy: {
    type: 'ajax',
    url: '/metrics/find/',
    extraParams: {query: '',
                  format: 'completer'
                 },
    reader: {
          type: 'json',
          root: 'metrics',
    }
  }
});

Ext.define('MetricCompleter', {
  extend: "Ext.form.ComboBox",
  displayField: "path",
  listEmptyText: "No matching metrics",
  mode: 'remote',
  hideTrigger: true,
  queryDelay: 100,
  queryParam: 'query',
  typeAhead: false,
  minChars: 1,
  store: store,
  listeners: {
   beforequery: function (e) {
                  this.store.proxy.extraParams.query = '*';
                }, 
   specialkey: function (queryEvent) {
    if (e.getKey() == e.TAB) { // This was a pain in the ass to actually get it working right
      field.getEl().blur();
      field.getEl().focus(50);
      field.doQuery( field.getValue() );
      e.stopEvent();
      return false;
               }
    },
   afterrender: function () {
        this.getEl().addListener('specialkey',
          function (el, e) {
            _this.onSpecialKey(_this.getEl(), e);
          }
        );
      }
    }
});

