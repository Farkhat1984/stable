# views/history_view.py
from kivy.factory import Factory
from front.views.invoice_history_item import InvoiceItemWidget
from kivy.uix.screenmanager import Screen
from front.controllers.history_api_controller import HistoryAPIController
from kivy.uix.popup import Popup
from kivy.uix.label import Label
from datetime import datetime, timedelta
from typing import List, Dict, Any
from front.utils.date_picker import CustomDatePicker as DatePicker

Factory.register('InvoiceItemWidget', InvoiceItemWidget)


class HistoryView(Screen):
    def __init__(self, screen_manager, **kwargs):
        super().__init__(name='history', **kwargs)
        self.sm = screen_manager
        self.sm.add_widget(self)
        self.api_controller: HistoryAPIController = None
        self.original_data: List[Dict[str, Any]] = []  # Добавляем хранение исходных данных
        self.current_data: List[Dict[str, Any]] = []
        self.sort_field: str = 'date'
        self.sort_reverse: bool = True
        self.current_grouping: str = None

        # Кэшируем ссылки на элементы интерфейса
        self.invoice_number_filter = self.ids.invoice_number_filter
        self.date_from_filter = self.ids.date_from
        self.date_to_filter = self.ids.date_to
        self.contact_filter = self.ids.contact_filter
        self.amount_from_filter = self.ids.amount_from
        self.amount_to_filter = self.ids.amount_to
        self.payment_status_filter = self.ids.payment_status
        self.invoice_list = self.ids.invoice_list

    def reset_filters(self) -> None:
        """Сброс всех фильтров и обновление списка."""
        self.invoice_number_filter.text = ''
        self.date_from_filter.text = ''
        self.date_to_filter.text = ''
        self.contact_filter.text = ''
        self.amount_from_filter.text = ''
        self.amount_to_filter.text = ''
        self.payment_status_filter.text = 'Все'
        self.current_data = self.original_data.copy()  # Восстанавливаем исходные данные
        self.update_display()
    def show_date_picker_from(self, instance):
        """Показать календарь для выбора начальной даты"""
        date_picker = DatePicker(callback=self.set_date_from)
        date_picker.open()

    def show_date_picker_to(self, instance):
        """Показать календарь для выбора конечной даты"""
        date_picker = DatePicker(callback=self.set_date_to)
        date_picker.open()

    def set_date_from(self, date_str):
        """Установить начальную дату"""
        self.date_from_filter.text = date_str

    def set_date_to(self, date_str):
        """Установить конечную дату"""
        self.date_to_filter.text = date_str

    def validate_date_range(self):
        """Проверка корректности диапазона дат"""
        if not self.date_from_filter.text or not self.date_to_filter.text:
            return True

        try:
            date_from = datetime.strptime(self.date_from_filter.text, "%Y-%m-%d")
            date_to = datetime.strptime(self.date_to_filter.text, "%Y-%m-%d")

            if date_from > date_to:
                self.show_message("Дата 'с' не может быть позже даты 'по'")
                return False

            # Проверка, что диапазон не превышает год
            if date_to - date_from > timedelta(days=365):
                self.show_message("Диапазон дат не может превышать один год")
                return False

            return True
        except ValueError:
            self.show_message("Неверный формат даты")
            return False

    def sort_invoices(self, field: str) -> None:
        """Сортировка накладных по заданному полю."""
        if self.sort_field == field:
            self.sort_reverse = not self.sort_reverse
        else:
            self.sort_field = field
            self.sort_reverse = False

        try:
            if field == 'total':
                self.current_data.sort(key=lambda x: float(x.get(field, 0.0)), reverse=self.sort_reverse)
            elif field == 'date':
                self.current_data.sort(key=lambda x: datetime.strptime(x.get(field, ), "%Y-%m-%d"),
                                       reverse=self.sort_reverse)
            else:
                self.current_data.sort(key=lambda x: x.get(field, '').lower(), reverse=self.sort_reverse)
            self.update_display()
        except Exception as e:
            self.show_message(f"Ошибка при сортировке: {str(e)}")

    def group_invoices(self, field: str) -> None:
        """Группировка накладных по заданному полю."""
        if not self.current_data:
            return

        self.current_grouping = field
        grouped_data = {}

        for invoice in self.current_data:
            key = invoice.get(field, 'Не указано')
            grouped_data.setdefault(key, []).append(invoice)

        display_data = []
        for key, group in sorted(grouped_data.items(), key=lambda x: x[0]):
            # Формирование заголовка группы
            if field == 'is_paid':
                header_text = 'Оплачено' if key else 'Не оплачено'
            else:
                header_text = str(key)
            total_amount = sum(float(inv.get('total', 0.0)) for inv in group)
            display_data.append({
                'is_group_header': True,
                'number': '',
                'date': '',
                'contact': f"{header_text} ({len(group)} шт.)",
                'total': f"{total_amount:.2f}",
                'is_paid': all(inv.get('is_paid', False) for inv in group)
            })
            display_data.extend(group)

        self.invoice_list.data = display_data

    def clear_grouping(self) -> None:
        """Очистка текущей группировки и обновление отображения."""
        self.current_grouping = None
        self.update_display()

    def update_display(self) -> None:
        """Обновление отображения списка накладных с учётом группировки."""
        if self.current_grouping:
            self.group_invoices(self.current_grouping)
        else:
            self.invoice_list.data = self.current_data

    def edit_invoice(self, invoice_id: int) -> None:
        """Редактирование выбранной накладной."""
        try:
            print(f"HistoryView: Loading invoice {invoice_id} for editing")  # Отладка

            def on_invoice_loaded(invoice_data: Dict[str, Any]):
                try:
                    print(f"HistoryView: Invoice data loaded: {invoice_data}")  # Отладка
                    invoice_view: Screen = self.sm.get_screen('invoice')
                    if invoice_view:
                        invoice_view.load_invoice_data(invoice_data)
                        self.sm.current = 'invoice'
                    else:
                        raise ValueError("Invoice view not found")
                except Exception as e:
                    print(f"Error in on_invoice_loaded: {e}")  # Отладка
                    self.show_message(f"Ошибка при загрузке данных накладной: {str(e)}")

            if self.api_controller:
                self.api_controller.get_invoice_details(
                    invoice_id,
                    success_callback=on_invoice_loaded,
                    error_callback=lambda error: self.show_message(f"Ошибка загрузки накладной: {error}")
                )
            else:
                raise ValueError("API controller not initialized")

        except Exception as e:
            print(f"Error in edit_invoice: {e}")  # Отладка
            self.show_message(f"Ошибка при редактировании накладной: {str(e)}")

    def on_invoices_loaded(self, result: List[Dict[str, Any]]) -> None:
        """Callback при успешной загрузке накладных."""
        try:
            invoice_data = [{
                'number': str(invoice.get('id', '')),
                'date': invoice.get('created_at', '').split('T')[0],
                'contact': invoice.get('contact_info', ''),
                'total': f"{invoice.get('total_amount', 0.0):.2f}",
                'is_paid': invoice.get('is_paid', False)
            } for invoice in result]
            self.original_data = invoice_data.copy()  # Сохраняем копию исходных данных
            self.current_data = invoice_data
            self.update_display()
        except Exception as e:
            print(f"Error in on_invoices_loaded: {e}")  # Отладка
            self.show_message(f"Ошибка обработки данных накладных: {str(e)}")
    def on_auth_controller(self, instance, value) -> None:
        """Установка API контроллера при изменении auth_controller."""
        if value:
            print(f"HistoryView: Setting auth_controller with token: {value.token}")  # Отладка
            self.api_controller = HistoryAPIController(auth_controller=value)
            # Проверяем наличие токена перед загрузкой
            if value.token:
                print("HistoryView: Token present, loading invoices")  # Отладка
                self.refresh_list()
            else:
                print("HistoryView: No token available")  # Отладка

    def update_invoice_in_list(self, updated_invoice: Dict[str, Any]) -> None:
        """Обновление конкретной накладной в списке."""
        try:
            invoice_number = str(updated_invoice.get('id'))
            for i, invoice in enumerate(self.current_data):
                if invoice['number'] == invoice_number:
                    self.current_data[i] = {
                        'number': invoice_number,
                        'date': updated_invoice.get('created_at', '').split('T')[0],
                        'contact': updated_invoice.get('contact_info', ''),
                        'total': f"{updated_invoice.get('total_amount', 0.0):.2f}",
                        'is_paid': updated_invoice.get('is_paid', False)
                    }
                    self.update_display()
                    break
        except Exception as e:
            print(f"Error in update_invoice_in_list: {e}")  # Отладка
            self.show_message(f"Ошибка при обновлении накладной: {str(e)}")

    def remove_invoice_from_list(self, invoice_id: int) -> None:
        """Удаление накладной из списка."""
        try:
            invoice_id_str = str(invoice_id)
            self.current_data = [inv for inv in self.current_data if inv['number'] != invoice_id_str]
            self.update_display()
        except Exception as e:
            print(f"Error in remove_invoice_from_list: {e}")  # Отладка
            self.show_message(f"Ошибка при удалении накладной: {str(e)}")

    def add_invoice_to_list(self, new_invoice: Dict[str, Any]) -> None:
        """Добавление новой накладной в список."""
        try:
            invoice_data = {
                'number': str(new_invoice.get('id', '')),
                'date': new_invoice.get('created_at', '').split('T')[0],
                'contact': new_invoice.get('contact_info', ''),
                'total': f"{new_invoice.get('total_amount', 0.0):.2f}",
                'is_paid': new_invoice.get('is_paid', False)
            }
            self.current_data.insert(0, invoice_data)  # Добавляем в начало списка
            self.update_display()
        except Exception as e:
            print(f"Error in add_invoice_to_list: {e}")  # Отладка
            self.show_message(f"Ошибка при добавлении накладной: {str(e)}")

    def show_message(self, message: str) -> None:
        """Показ всплывающего сообщения пользователю."""
        popup = Popup(
            title='Сообщение',
            content=Label(text=message),
            size_hint=(None, None),
            size=(400, 200)
        )
        popup.open()

    def on_load_error(self, error: str) -> None:
        """Callback при ошибке загрузки накладных."""
        print(f"HistoryView: Load error: {error}")  # Отладка
        self.show_message(f"Ошибка загрузки накладных: {error}")

    def search_invoices(self, instance=None) -> None:
        """Поиск накладных по заданным фильтрам."""
        if not self.validate_date_range():
            return

        # Начинаем фильтрацию с исходных данных
        filtered_data = self.original_data.copy()

        try:
            # Фильтр по номеру накладной
            if self.invoice_number_filter.text:
                filtered_data = [
                    inv for inv in filtered_data
                    if self.invoice_number_filter.text.strip().lower() in inv['number'].lower()
                ]

            # Фильтр по датам
            if self.date_from_filter.text:
                date_from = datetime.strptime(self.date_from_filter.text, "%Y-%m-%d")
                filtered_data = [
                    inv for inv in filtered_data
                    if datetime.strptime(inv['date'], "%Y-%m-%d") >= date_from
                ]

            if self.date_to_filter.text:
                date_to = datetime.strptime(self.date_to_filter.text, "%Y-%m-%d")
                filtered_data = [
                    inv for inv in filtered_data
                    if datetime.strptime(inv['date'], "%Y-%m-%d") <= date_to
                ]

            # Фильтр по контрагенту
            if self.contact_filter.text:
                search_contact = self.contact_filter.text.strip().lower()
                filtered_data = [
                    inv for inv in filtered_data
                    if search_contact in inv['contact'].lower()
                ]

            # Фильтр по сумме
            if self.amount_from_filter.text:
                min_amount = float(self.amount_from_filter.text)
                filtered_data = [
                    inv for inv in filtered_data
                    if float(inv['total']) >= min_amount
                ]

            if self.amount_to_filter.text:
                max_amount = float(self.amount_to_filter.text)
                filtered_data = [
                    inv for inv in filtered_data
                    if float(inv['total']) <= max_amount
                ]

            # Фильтр по статусу оплаты
            if self.payment_status_filter.text != 'Все':
                is_paid = self.payment_status_filter.text == 'Оплачено'
                filtered_data = [
                    inv for inv in filtered_data
                    if inv['is_paid'] == is_paid
                ]

            # Обновляем текущие данные и отображение
            self.current_data = filtered_data
            self.update_display()

        except ValueError as e:
            self.show_message(f"Ошибка в формате данных: {str(e)}")
        except Exception as e:
            print(f"Error in search_invoices: {e}")  # Отладка
            self.show_message(f"Ошибка при поиске накладных: {str(e)}")
    def refresh_list(self, instance=None) -> None:
        """Обновление списка накладных без фильтров."""
        if not self.api_controller:
            print("HistoryView: No API controller")  # Отладка
            self.show_message("API контроллер не инициализирован")
            return

        if not self.sm.get_screen('invoice').auth_controller or not self.sm.get_screen('invoice').auth_controller.token:
            print("HistoryView: No auth token")  # Отладка
            self.show_message("Необходима авторизация для обновления списка накладных")
            return

        print(
            f"HistoryView: Refreshing list with token: {self.sm.get_screen('invoice').auth_controller.token}")  # Отладка
        self.api_controller.get_invoices(
            success_callback=self.on_invoices_loaded,
            error_callback=self.on_load_error
        )

    def delete_invoice(self, invoice_id: int) -> None:
        """Удаление накладной по ID."""
        try:
            def on_delete_success():
                self.show_message("Накладная успешно удалена")
                self.refresh_list()

            def on_delete_error(error: str):
                self.show_message(f"Ошибка удаления накладной: {error}")

            if self.api_controller:
                self.api_controller.delete_invoice(
                    invoice_id,
                    success_callback=on_delete_success,
                    error_callback=on_delete_error
                )
            else:
                self.show_message("API контроллер не инициализирован")
        except Exception as e:
            print(f"Error in delete_invoice: {e}")  # Отладка
            self.show_message(f"Ошибка при удалении накладной: {str(e)}")