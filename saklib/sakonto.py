# -*- coding: UTF-8 -*-

__author__ = "Fernando Witt"
__credits__ = ["Fernando Witt"]

__license__ = "MIT"
__maintainer__ = "Fernando Witt"
__email__ = "ferawitt@gmail.com"

from sakconfig import SAK_GLOBAL, SAK_LOCAL, CURRENT_DIR

from io import StringIO  ## for Python 3
from contextlib import redirect_stderr

import os
import urllib
from pathlib import Path
import uuid
import panel as pn
import param

from functools import partial

class Sak(object):
    """Sak base class"""
    def __init__(self, name=None, **vargs):
        if name is not None:
            name = urllib.parse.quote(name, safe='')
        else:
            name = uuid.uuid4().hex

        self.name = name
        self.extra_args = vargs

    def get_name(self):
        return urllib.parse.unquote(self.name)


    def property_editor(self, set_content):

        ret = pn.Column()

        ## TODO(witt): Edit
        #   DONE       - name
        #   DONE       - iri
        #   DONE       - label
        #   DONE       - Data Functional properties (str, int, ...)
        #   DONE       - Data Non functional properties (str, int, ...)
        #              - Object properties (Functional and non Functional)
        #   DONE       - Add data property
        #              - Add object property
        #              - Destroy element

        def __destroy(object_to_destroy, event):
            owl.destroy_entity(object_to_destroy)
            save_ontologies(True)
            set_content()

        destroy_button = pn.widgets.Button(name='Destroy', width=40)
        destroy_button.on_click(partial(__destroy, self))
        ret.append(destroy_button)


        def __delete(prop_name, prop_pos, event):
            if prop_pos is None:
                setattr(self, prop_name, None)
            else:
                getattr(self, prop_name).pop(prop_pos)
            save_ontologies(True)
            set_content()

        def __update(prop_name, prop_pos, text_input, event):
            if prop_pos is None:
                setattr(self, prop_name, text_input.value)
            else:
                getattr(self, prop_name)[prop_pos] = text_input.value
            save_ontologies(True)
            set_content()

        def __get_widget(prop_name, prop_pos, prop_type, enable_update=True, enable_delete=True):

            if prop_pos is None:
                prop_value = getattr(self, prop_name)
            else:
                prop_value = getattr(self, prop_name)[prop_pos]

            if prop_type is str:
                text_input = pn.widgets.TextInput(name=prop_name, value=prop_value)
            elif prop_type is int:
                text_input = pn.widgets.Spinner(name=prop_name, value=prop_value, step=1)

            ret = pn.Row(text_input)

            if enable_update:
                update_button = pn.widgets.Button(name='Update', width=40)
                update_button.on_click(partial(__update, prop_name, prop_pos, text_input))
                ret.append(update_button)

            if enable_delete:
                delete_button = pn.widgets.Button(name='Delete', width=40)
                delete_button.on_click(partial(__delete, prop_name, prop_pos))
                ret.append(delete_button)

            return ret

        ret.append(__get_widget('name', None, str, enable_delete=False))

        if self.label:
            ret.append(__get_widget('label', None, str, enable_delete=True))

        for prop in self.get_properties():
            if owl.FunctionalProperty in prop.is_a:
                if str in prop.range:
                    _prop_editor = __get_widget(prop.name, None, str)
                    ret.append(_prop_editor)
                if int in prop.range:
                    _prop_editor = __get_widget(prop.name, None, int)
                    ret.append(_prop_editor)
            else:
                for i in range(len(getattr(self, prop.name))):
                    if str in prop.range:
                        _prop_editor = __get_widget(prop.name, i, str)
                        ret.append(_prop_editor)
                    if int in prop.range:
                        _prop_editor = __get_widget(prop.name, i, int)
                        ret.append(_prop_editor)


        add_props = []
        for prop in owl.default_world.data_properties():
            is_in_range = False
            for self_is_a in self.is_a:
                if self_is_a in prop.domain:
                    is_in_range = True
                for domain in prop.domain:
                    if isinstance(self_is_a, domain):
                        is_in_range = True
                        break
                if is_in_range:
                    break
            if is_in_range:
                add_props.append(prop)

        add_prop_obj_selector = []

        # TODO: Nao posso criar essa classe sob demanda?
        class PropValue():
            def __init__(self, obj, prop, set_content):
                self.obj = obj
                self.prop = prop
                self.prop_type = str
                self.set_content = set_content

                if int in self.prop.range:
                    self.prop_type = int

            @property
            def name(self):
                return self.prop.name

            def __add(self, text_input, event):
                if owl.FunctionalProperty in self.prop.is_a:
                    setattr(self.obj, self.prop.name, text_input.value)
                else:
                    getattr(self.obj, self.prop.name).append(text_input.value)

                save_ontologies(True)
                self.set_content()

            def view(self):
                ret = pn.Row()

                if self.prop_type is str:
                    text_input = pn.widgets.TextInput(name=self.prop.name)
                elif self.prop_type is int:
                    text_input = pn.widgets.Spinner(name=self.prop.name)

                ret.append(text_input)

                add_button = pn.widgets.Button(name='Add', width=40)
                add_button.on_click(partial(self.__add, text_input))
                ret.append(add_button)

                return ret

        for prop in add_props:
            add_prop_obj_selector.append(PropValue(self, prop, set_content))

        class DataPropAdder(param.Parameterized):
            prop = param.ObjectSelector(add_prop_obj_selector[0], objects=add_prop_obj_selector)

            @param.depends('prop')
            def view(self):
                return self.prop.view()

            def panel(self):
                return pn.Column(self.param, self.view)

        ret.append(DataPropAdder().panel())
        return ret


    def panel(self):
        tab_content = pn.Column(
                sizing_mode='stretch_width'
                )

        def set_content():
            tab_content.clear()
            tab_content.append(pn.pane.Markdown(f'''\
                # {self.name}

                name: {self.name}

                iri: {self.iri}
            ''' ))

        set_content()

        return pn.Tabs(('SAK', tab_content),
                sizing_mode='stretch_width',
                )

